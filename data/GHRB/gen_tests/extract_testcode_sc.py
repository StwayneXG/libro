import pandas as pd
import os

def main():
    experiment = "meaningfulmask_0-rephrased"
    df = pd.read_csv(f"{experiment}_generatedtestcases.csv")
    df['Generated Testcases'] = df['Generated Testcases'].apply(eval)
    os.makedirs(experiment, exist_ok=True)

    for i, row in df.iterrows():
        project = row['Project']
        bug_number = row['Bug Number']
        testcases = row['Generated Testcases']

        for j, testcase in enumerate(testcases):
            if not testcase.startswith("public void test"):
                testcase = "public void test" + testcase
            with open(f"{experiment}/{project}_{bug_number}_n{j}.txt", "w", errors='ignore') as f:
                f.write(testcase)

if __name__ == "__main__":
    main()