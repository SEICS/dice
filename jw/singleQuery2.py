import subprocess, re
import json
import itertools

output = subprocess.getoutput("./Dice.native jw/bayescard_test.dice").split("\n")[1:-2]
with open("jw/queries.json","r") as jsonstr1:
    queries = json.load(jsonstr1)

with open("jw/attr_range.json","r") as jsonstr2:
    attr_range = json.load(jsonstr2)

query = queries[43]
order = dict()

for q in query.keys():
    attr = query[q]
    limit = attr_range[q]
    for num in attr:
        if num < 0 or num > limit:
            attr.remove(num)

for q in query.keys():
    if query[q] == []:
        query.remove(q)

names = list(query.keys())
print(names)
for n in names:
    order[n] = names.index(n)

vals = list(query.values())
vals = [list(v) for v in list(itertools.product(*vals))]

combination = dict()
for l in output:
    line = l.split("\t")
    prob = line[-1]
    combo = re.findall("[0-9]+", line[0])
    combo = [n for n in combo]
    combination[",".join(combo)] = float(prob.strip())

probs = 0
for v in vals:
    for c in combination.keys():
        c2 = [int(cc) for cc in c.split(",")]
        check = all([True if vv == cc else False for vv,cc in zip(v,c2)])
        if check:
            probs += combination[c]


predict = probs * 2458285
true_cardinality = 398593
q_error = max(predict/true_cardinality, true_cardinality/predict)
print(q_error)
    