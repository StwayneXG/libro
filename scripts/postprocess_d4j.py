from os import path
from common import *
from config import llm_exp_config
from collections import defaultdict
from tqdm import tqdm
import time

import os
import re
import glob
import subprocess as sp
import argparse
import d4j_util

import pandas as pd
from masker import mask_method

# MASK_INFO_DIR = '/root/data/Defects4J/mask_data/meaningfulmask_0'
# MASK_INFO_DIR = '/root/data/Defects4J/mask_data/hashmask'
MASK_INFO_DIR = None

def inject_prefix_rootdir(proj, bug_id):
    rpath = d4j_util.repo_path(proj, bug_id)
    return rpath


def enforce_static_assertions(gen_test):
    if 'Assert.' in gen_test:
        # force to use static assertion imports
        gen_test = gen_test.replace('Assert.fail', 'fail')
        gen_test = gen_test.replace('Assert.assert', 'assert')
    return gen_test


def needed_imports_by_bug_id(proj, bug_id, gen_test):
    repo_path = d4j_util.repo_path(proj, bug_id)
    src_dir = d4j_util.d4j_path_prefix(proj, bug_id)

    classpaths, needed_class_stubs, needed_asserts = needed_imports(
        repo_path, src_dir, gen_test)

    return classpaths, needed_asserts


def add_test_by_bug_id(proj, bug_id, gen_test, needed_elements, dry=False):
    repo_path = d4j_util.repo_path(proj, bug_id)
    test_prefix = d4j_util.d4j_test_path_prefix(proj, bug_id)

    # proj is needed to obtain project identifier (e.g., jackson.core)
    return add_test(proj, repo_path, test_prefix, gen_test, needed_elements, dry=dry)


def inject_test_by_bug_id(proj, bug_id, gen_test, needed_elements, dry=False):
    repo_path = inject_prefix_rootdir(proj, bug_id)
    src_dir = d4j_util.d4j_path_prefix(proj, bug_id)
    test_dir = d4j_util.d4j_test_path_prefix(proj, bug_id)

    return inject_test(repo_path, src_dir, test_dir, gen_test, needed_elements, dry=dry)


def git_reset(repo_dir_path):
    sp.run(['git', 'reset', '--hard', 'HEAD'],
           cwd=repo_dir_path, stdout=sp.DEVNULL, stderr=sp.DEVNULL)


def git_clean(repo_dir_path):
    sp.run(['git', 'clean', '-df'],
           cwd=repo_dir_path, stdout=sp.DEVNULL, stderr=sp.DEVNULL)


def git_d4j_handle(repo_dir_path, ref_tag):
    sp.run(['git', 'checkout', ref_tag, '--', '.defects4j.config'],
           cwd=repo_dir_path)
    sp.run(['git', 'checkout', ref_tag, '--', 'defects4j.build.properties'],
           cwd=repo_dir_path)


def compile_repo(repo_dir_path):
    # actual compiling
    compile_proc = sp.run(
        ['defects4j', 'compile'],
        stdout=sp.PIPE, stderr=sp.PIPE, cwd=repo_dir_path)

    # extracting error message
    compile_error_lines = compile_proc.stderr.decode('utf-8').split('\n')[2:]
    compile_error_lines = [
        e for e in compile_error_lines if '[javac] [' not in e]
    compile_error_lines = [e for e in compile_error_lines if '[javac]' in e]
    compile_error_lines = [
        e for e in compile_error_lines if 'warning:' not in e]
    compile_error_lines = [
        e for e in compile_error_lines if '[javac] Note:' not in e]
    compile_error_lines = [
        e for e in compile_error_lines if 'compiler be upgraded.' not in e]
    compile_error_msg = '\n'.join(compile_error_lines)
    return compile_proc.returncode, compile_error_msg


def run_test(repo_dir_path, test_name):
    '''Returns failing test number.'''
    test_process = sp.run(['timeout', '20m', 'defects4j', 'test', '-t', test_name],
                          capture_output=True, cwd=repo_dir_path)
    captured_stdout = test_process.stdout.decode()
    if len(captured_stdout) == 0:
        return -1, []  # likely compile error, all tests failed
    else:
        stdout_lines = captured_stdout.split('\n')
        failed_test_num = int(stdout_lines[0].removeprefix('Failing tests: '))
        failed_tests = [e.strip(' - ') for e in stdout_lines[1:] if len(e) > 1]
        # reported failing test number and actual number of collected failing tests should match
        assert len(failed_tests) == failed_test_num

        return 0, failed_tests

def individual_run(proj, bug_id, example_test, injection):
    # test class generation & addition
    repo_path = inject_prefix_rootdir(proj, bug_id) if injection else d4j_util.repo_path(proj, bug_id)

    start_masking = time.time()
    if MASK_INFO_DIR is not None:
        mask_info = pd.read_csv(path.join(MASK_INFO_DIR, f'{proj}-{bug_id}.csv'))
        for i, row in mask_info.iterrows():
            mask_method(repo_path, row['Old Method Name'], row['New Method Name'])
    end_masking = time.time()
    # print(f'Masking for {proj}-{bug_id} took {end_masking-start_masking:.2f}s')

    start_inject = time.time()
    needed_elements = needed_imports_by_bug_id(proj, bug_id, example_test)
    test_add_func = inject_test_by_bug_id if injection else add_test_by_bug_id
    test_name = test_add_func(proj, bug_id, example_test, needed_elements)
    end_inject = time.time()
    print(f'Injecting for {proj}-{bug_id} took {end_inject-start_inject:.2f}s')

    start_compile = time.time()
    # actual running experiment
    fib_error_msg = None
    compile_status, compile_msg = compile_repo(repo_path)
    end_compile = time.time()
    print(f'Compiling for {proj}-{bug_id} took {end_compile-start_compile:.2f}s')
    if compile_status != 0:
        status = -2
        failed_tests = []
    else:
        start_test = time.time()
        status, failed_tests = run_test(repo_path, test_name)
        end_test = time.time()
        print(f'Testing for {proj}-{bug_id} took {end_test-start_test:.2f}s')
        if len(failed_tests) > 0:
            with open(path.join(repo_path, 'failing_tests')) as f:
                fib_error_msg = ''.join(f.readlines()[:5])

    if fib_error_msg is not None and 'not found' in fib_error_msg:
        print(f'Warning; test not found for {proj}-{bug_id}:{test_name}.')

    return {
        'compile_error': status == -2,
        'runtime_error': status == -1,
        'failed_tests': failed_tests,
        'autogen_failed': len(failed_tests) > 0,
        'fib_error_msg': fib_error_msg,
        'compile_msg': compile_msg if status == -2 else None
    }


def twover_run_experiment(proj, bug_id, test_files, example_tests, res_for_bug, injection=True):
    """
    returns results in order of example_tests.
    """
    print(f'Running experiment for {proj}-{bug_id} (injection={injection})')

    # init
    repo_path = inject_prefix_rootdir(proj, bug_id) if injection else d4j_util.repo_path(proj, bug_id)
    test_dir = d4j_util.d4j_test_path_prefix(proj, bug_id)
    git_reset(repo_path)
    git_clean(repo_path)
    d4j_process = sp.run(['defects4j', 'export', '-p', 'dir.bin.tests'],
                          capture_output=True, cwd=repo_path)
    test_class_dir = d4j_process.stdout.decode()
    etc_info = ''

    buggy_results = []
    fixed_results = []
    final_results = []
    for x, example_test in enumerate(example_tests):
        # Running experiment for buggy version
        git_reset(repo_path)
        git_clean(repo_path)
        pretag = 'PRE_FIX_COMPILABLE' if injection else 'BUGGY_VERSION'
        cp = sp.run(['git', 'checkout', f'D4J_{proj}_{bug_id}_{pretag}'],
                    cwd=repo_path, stdout=sp.DEVNULL, stderr=sp.DEVNULL)
        if cp.returncode != 0:
            return None
        # print(f'Running PRE test {x+1}/{len(example_tests)}')
        git_reset(repo_path)
        git_clean(repo_path)
        example_test = enforce_static_assertions(example_test)
        try:
            buggy_info = individual_run(proj, bug_id, example_test, injection)
        except Exception as e:
            buggy_info = f'[error] {repr(e)}'

        buggy_results.append(buggy_info)

        # Running experiment for fixed version
        git_reset(repo_path)
        git_clean(repo_path)
        posttag = 'POST_FIX_PRE_TEST_COMPILABLE' if injection else 'FIXED_VERSION'
        cp = sp.run(['git', 'checkout', f'D4J_{proj}_{bug_id}_{posttag}'],
                    cwd=repo_path, capture_output=True)
        if cp.returncode != 0:
            cp = sp.run(['git', 'checkout', f'D4J_{proj}_{bug_id}_POST_FIX_REVISION'],
                    cwd=repo_path, capture_output=True)
        if cp.returncode != 0:
            return None
    # for x, example_test in enumerate(example_tests):
        # print(f'Running POST test {x+1}/{len(example_tests)}')
        git_reset(repo_path)
        if injection:
            git_clean(repo_path)
        example_test = enforce_static_assertions(example_test)
        try:
            fixed_info = individual_run(proj, bug_id, example_test, injection)
        except Exception as e:
            fixed_info = f'[error] {repr(e)}'

        fixed_results.append(fixed_info)

        # print(f'Buggy Results: {buggy_results}')
        # print(f'Fixed Results: {fixed_results}')

        # Matching results together
        final_results = []
        for buggy_info, fixed_info in zip(buggy_results, fixed_results):
            if isinstance(buggy_info, str): # Test is syntactically incorrect (JavaSyntaxError)
                final_results.append(buggy_info)
                continue

            if isinstance(fixed_info, str): # Test is syntactically incorrect (JavaSyntaxError)
                final_results.append(fixed_info)
                continue

            fails_in_buggy_version = any(map(lambda x: 'AutoGen' in x, buggy_info['failed_tests']))
            fails_in_fixed_version = any(map(lambda x: 'AutoGen' in x, fixed_info['failed_tests']))

            success = (fails_in_buggy_version and not fails_in_fixed_version)

            final_results.append({
                'buggy': buggy_info,
                'fixed': fixed_info,
                'success': success,
            })

        # print(f"Final results: {final_results}")

        # print(f'Test Files: {test_files}')

        # print(f"Resforbug: {res_for_bug}")

        for test_path, res in zip(test_files, final_results):
            # print(f'Adding results for {os.path.basename(test_path)}')
            res_for_bug[os.path.basename(test_path)] = res

        # print(f"Saving results for {proj}-{bug_id}")
        # print(res_for_bug)

        os.makedirs(f'/root/results/{args.experiment_name}', exist_ok=True)
        if len(res_for_bug.keys()) > 0:
            with open(f'/root/results/{args.experiment_name}/{args.project}_{args.bug_id}.json', 'w') as f:
                json.dump(res_for_bug, f, indent=4)

    return final_results

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--project', required=True)
    parser.add_argument('-b', '--bug_id', type=int, required=True)
    parser.add_argument('--experiment_name', required=True)
    args = parser.parse_args()

    GEN_TEST_DIR = f'/root/data/Defects4J/gen_tests/{args.experiment_name}'

    test_files = glob.glob(os.path.join(GEN_TEST_DIR, f'{args.project}_{args.bug_id}_*.txt'))
    example_tests = []
    res_for_bug = {}

    # If the results file already exists, update the results dict with the results
    if os.path.exists(f'/root/results/{args.experiment_name}/{args.project}_{args.bug_id}.json'):
        with open(f'/root/results/{args.experiment_name}/{args.project}_{args.bug_id}.json') as f:
            res_for_bug = json.load(f)

    # Remove test files that have already been processed
    test_files = [x for x in test_files if os.path.basename(x) not in res_for_bug.keys()]

    for x, gen_test_file in enumerate(test_files):
        with open(gen_test_file, errors='ignore') as f:
            test_content = f.read().strip()
            if test_content.startswith('```'):
                test_content = test_content.removeprefix('```')
            if test_content.endswith('```'):
                test_content = test_content.removesuffix('```')

            example_tests.append(test_content)

    start = time.time()
    results = twover_run_experiment(args.project, args.bug_id, test_files, example_tests, res_for_bug)
    end = time.time()
    os.makedirs('/root/results/timelogs/', exist_ok=True)
    os.makedirs(f'/root/results/timelogs/{args.experiment_name}', exist_ok=True)
    if not os.path.exists(f'/root/results/timelogs/{args.experiment_name}/{args.project}_{args.bug_id}.txt'):
        with open(f'/root/results/timelogs/{args.experiment_name}/{args.project}_{args.bug_id}.txt', 'w') as f:
            f.write(f'{end-start:.2f}')
    print(f'Experiment for {args.project}-{args.bug_id} took {end-start:.2f}s')

    for test_path, res in zip(test_files, results):
        res_for_bug[os.path.basename(test_path)] = res

    os.makedirs(f'/root/results/{args.experiment_name}', exist_ok=True)
    if len(res_for_bug.keys()) > 0:
        with open(f'/root/results/{args.experiment_name}/{args.project}_{args.bug_id}.json', 'w') as f:
            json.dump(res_for_bug, f, indent=4)