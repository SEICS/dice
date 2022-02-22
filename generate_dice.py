import pandas as pd
import json 

df = pd.read_csv("~/Desktop/BayesCard/discrete_table.csv", header=0, sep=",")

def writeDice(relation):
    global df
    dice = []
    from Models.automateModel import tree_structure, construct_tree, findSingleNodePath
    parents, children, nodes = tree_structure(relation)
    nodes_lis, nodes_name, allPath = construct_tree(parents, children, nodes) # produce tree graph "BN_Chow_liu_tree.png"
    
    with open("pgmpyCPD.json","r") as f:
        cpds = json.load(f)
        
    # write dice file
    for n in nodes_name: 
        if not parents[n]:
            cpd = [str(cpd) for cpd in cpds[n][0]] # root node
            dice.append("let " + n + " = discrete(" + ",".join(cpd) + ") in\n" )
        else:
            cpd = []
            par = parents[n][0]
            for c in cpds[n]:
                cpd.append([str(cc) for cc in c])
                   
            leng = len(cpd)
            # print("leng: ",leng)
            line = ["let " + n + " = "]
            
            for idx in range(len(cpd)):
                c = cpd[idx]
                # print(n + "[" + str(idx) + "]" + ": " + ",".join(c))
                
                if idx == len(cpd)-2: # last two
                    if len(cpd) == 2:
                        line.append("if (" + par + " == int(" + str(leng) + "," + str(idx) + ")) then (discrete(" + ",".join(c) + ")) else (discrete(" + ",". join(cpd[-1]) + "))")
                    else:
                        line.append("(if (" + par + " == int(" + str(leng) + "," + str(idx) + ")) then (discrete(" + ",".join(c) + ")) else (discrete(" + ",". join(cpd[-1]) + "))")
                    break
                elif idx == 0: # start
                    line.append("if (" + par + " == int(" + str(leng) + "," + str(idx) + ")) then (discrete(" + ",".join(c) + ")) else ")
                else:
                    line.append("(if (" + par + " == int(" + str(leng) + "," + str(idx) + ")) then (discrete(" + ",".join(c) + ")) else ")
                
            line.append(")" * (len(cpd)-2) + " in\n")
            
            dice.append("".join(line))
        
            # dice.append("let " + n + " = if ((" + par + " == int(" + str(attr_range[par]-1) + ",0))) then (discrete(" + ",".join(cpd_T) + ")) else (discrete(" + ",".join(cpd_F) + ")) in\n")
    
    with open("queries.json","r") as q:
        queries = json.load(q)
        
    for query in queries:
        attrs = list(query.keys())
        l = "\n"
        for n in attrs:
            if attrs.index(n) == len(attrs)-1:
                l += "(" + n 
            else:
                l += "(" + n + ","
        l += ")" * len(attrs)
        
        dice.append(l)
               
    with open("benchmark_BN.dice", "w+") as f:
        f.write("".join(dice))

                
if __name__ == "__main__":
    relation = [('iLang1', 'dAncstry1'), ('dAncstry1', 'dAncstry2'), ('iLooking', 'iAvail'), ('iRPOB', 'iCitizen'), ('dIndustry', 'iClass'), ('dTravtime', 'dDepart'), ('iDisabl2', 'iDisabl1'), ('iYearwrk', 'iDisabl2'), ('iLang1', 'iEnglish'), ('iRvetserv', 'iFeb55'), ('iRelat1', 'iFertil'), ('dAncstry1', 'dHispanic'), ('iWork89', 'dHour89'), ('iRlabor', 'dHours'), ('iRPOB', 'iImmigr'), ('dRearning', 'dIncome1'), ('iClass', 'dIncome2'), ('dOccup', 'dIncome3'), ('dRpincome', 'dIncome4'), ('dAge', 'dIncome5'), ('dRpincome', 'dIncome6'), ('dAge', 'dIncome7'), ('dRpincome', 'dIncome8'), ('dOccup', 'dIndustry'), ('iRvetserv', 'iKorean'), ('iYearsch', 'iLang1'), ('iRlabor', 'iLooking'), ('iRspouse', 'iMarital'), ('iRvetserv', 'iMay75880'), ('dHours', 'iMeans'), ('iRlabor', 'iMilitary'), ('iLang1', 'iMobility'), ('iDisabl1', 'iMobillim'), ('iYearwrk', 'dOccup'), ('iRvetserv', 'iOthrserv'), ('iMobillim', 'iPerscare'), ('dAncstry1', 'dPOB'), ('iRelat1', 'dPoverty'), ('iRPOB', 'dPwgt1'), ('iFertil', 'iRagechld'), ('dHour89', 'dRearning'), ('iRspouse', 'iRelat1'), ('iRelat1', 'iRelat2'), ('iRrelchld', 'iRemplpar'), ('iMeans', 'iRiders'), ('iYearwrk', 'iRlabor'), ('iRemplpar', 'iRownchld'), ('dRearning', 'dRpincome'), ('dPOB', 'iRPOB'), ('dAge', 'iRrelchld'), ('dAge', 'iRspouse'), ('iMilitary', 'iRvetserv'), ('dAge', 'iSchool'), ('iRvetserv', 'iSept80'), ('iRagechld', 'iSex'), ('iRelat1', 'iSubfam1'), ('iSubfam1', 'iSubfam2'), ('iRlabor', 'iTmpabsnt'), ('iMeans', 'dTravtime'), ('iRvetserv', 'iVietnam'), ('dRearning', 'dWeek89'), ('iYearwrk', 'iWork89'), ('iRlabor', 'iWorklwk'), ('iRvetserv', 'iWWII'), ('dAge', 'iYearsch'), ('dAge', 'iYearwrk'), ('iRvetserv', 'dYrsserv')]
    writeDice(relation)
   