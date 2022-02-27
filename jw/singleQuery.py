import subprocess, re
import json
import itertools
from time import perf_counter
import numpy as np

with open("true_cardinality.json","r") as j:
    true_cardinalities = json.load(j)

with open("queries.json","r") as j2:
    queries = json.load(j2)

with open("attr_range.json","r") as j3:
    attr_range = json.load(j3)

i = 43
query = queries[43]
order = dict()

print(f"Predicting cardinality for query {i}: {query}")
card_start_t = perf_counter()

for q in query.keys():
    attr = query[q]
    limit = attr_range[q]
    for num in attr:
        if num < 0 or num >= limit:
            attr.remove(num)

for q in list(query.keys()):
    attr = query[q]
    limit = attr_range[q]
    if len(attr) == limit:
        query.pop(q)

for q in query.keys():
    if query[q] == []:
        query.remove(q)

vals = list(query.values())
output = subprocess.getoutput("~/Desktop/dice/Dice.native bayescard_test.dice").split("\n")[1:-2]
probs = 0
for l in output:
    line = l.split("\t")
    prob = float(line[-1].strip())
    combo = re.findall("[0-9]+", line[0])
    combo = [int(n) for n in combo]
    check = all([True if combo[i] in vals[i] else False for i in range(len(vals))])
    if check:
        probs += prob

card_end_t = perf_counter()
latency_ms = (card_end_t-card_start_t) * 1000
cardinality_predict = probs * 2458285
cardinality_true = true_cardinalities[i]

# print(f"cardinality predict: {cardinality_predict} and cardinality true: {cardinality_true}")
if cardinality_predict == 0 and cardinality_true == 0:
    q_error = 1.0
elif np.isnan(cardinality_predict) or cardinality_predict == 0:
    cardinality_predict = 1
    q_error = max(cardinality_predict / cardinality_true, cardinality_true / cardinality_predict)
elif cardinality_true == 0:
    cardinality_true = 1
    q_error = max(cardinality_predict / cardinality_true, cardinality_true / cardinality_predict)
else:
    q_error = max(cardinality_predict / cardinality_true, cardinality_true / cardinality_predict)
print(f"latency: {latency_ms} and error: {q_error}")