import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.pyplot import savefig

df = pd.read_csv('hp_code_lines.csv')
# print(df)
# df.to_csv('hp_code_lines.csv', index=False)

# tips = sns.load_dataset("tips")
sns.set(style="whitegrid", color_codes=True)
sns.stripplot(x="label", y="lines", data=df)
plt.show()

sns.violinplot(x="label", y="lines", data=df, inner=None)  # inner 小提琴内部图形
sns.swarmplot(x="label", y="lines", data=df, color="w", alpha=.5)  # alpha 透明度
savefig('hp_code_1.png')
plt.show()


# sns.violinplot(x="label", y="lines", data=df, inner=None)
# sns.swarmplot(x="label", y="lines", data=df, color="w",)
# plt.show()
