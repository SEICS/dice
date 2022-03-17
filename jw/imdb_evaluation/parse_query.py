import logging
import pickle
from DeepDBUtils.ensemble_compilation.spn_ensemble import SPNEnsemble, _build_reverse_spn_dict
from DeepDBUtils.evaluation.utils import parse_query
from Evaluation.parse_query_imdb import factor_refine, generate_factors, prepare_single_query
from DeepDBUtils.aqp_spn.aqp_spn import AQPSPN
from DeepDBUtils.ensemble_compilation.probabilistic_query import Expectation, IndicatorExpectation

def read_ensemble(ensemble_locations, build_reverse_dict=False):
    """
    Creates union of all SPNs in the different ensembles.
    :param min_sample_ratio:
    :param ensemble_locations: list of file locations of ensembles.
    :return:
    """
    if not isinstance(ensemble_locations, list):
        ensemble_locations = [ensemble_locations]

    ensemble = SPNEnsemble(None)
    for ensemble_location in ensemble_locations:
        with open(ensemble_location, 'rb') as handle:
            current_ensemble = pickle.load(handle)
            ensemble.schema_graph = current_ensemble.schema_graph
            for spn in current_ensemble.spns:
                logging.debug(f"Including SPN with table_set {spn.table_set} with sampling ratio"
                              f"({spn.full_sample_size} / {spn.full_join_size})")
                # logging.debug(f"Stats: ({get_structure_stats(spn.mspn)})")
                # build reverse dict.
                if build_reverse_dict:
                    _build_reverse_spn_dict(spn)
                ensemble.add_spn(spn)
    return ensemble

def prepare_join_queries(ensemble_location, pairwise_rdc_path, query_filename,
                         join_3_rdc_based, true_card_exist=False):
    spn_ensemble = read_ensemble(ensemble_location, build_reverse_dict=True)

    '''
    set full join size for each spn manully
    '''
    if join_3_rdc_based:
        spn_ensemble.spns[0].full_join_size = 38028991
        spn_ensemble.spns[1].full_join_size = 70900181
        spn_ensemble.spns[2].full_join_size = 14883333
        spn_ensemble.spns[3].full_join_size = 3448422
        spn_ensemble.spns[4].full_join_size = 4050205
        spn_ensemble.spns[5].full_join_size = 36306324
        spn_ensemble.spns[6].full_join_size = 6575448

    parsed_queries = []

    with open(pairwise_rdc_path, 'rb') as handle:
        rdc_attribute_dict = pickle.load(handle)
    
    schema = spn_ensemble.schema_graph
    
    # --------------------------------------
    # print("rdc_attribute_dict: ",rdc_attribute_dict)
    with open(pairwise_rdc_path + "rdc_values.json","w+") as ff:
        import json
        my_rdc = {}
        for rdc in rdc_attribute_dict.keys():
            my_rdc[str(list(rdc))] = rdc_attribute_dict[rdc]
        json.dump(my_rdc,ff,indent=2)
    # print("prepare_join_queries_schema: ",schema)
    # --------------------------------------
    
    true_card = []
    with open(query_filename) as f:
        queries = f.readlines()
        for query_no, query_str in enumerate(queries):
            if true_card_exist:
                true_card.append(int(query_str.split("||")[-1]))
                query_str = query_str.split("||")[0]
            query_str = query_str.strip()

            query = parse_query(query_str.strip(), schema)

            first_spn, next_mergeable_relationships, next_mergeable_tables = \
                spn_ensemble._greedily_select_first_cardinality_spn(
                    query, rdc_spn_selection=True, rdc_attribute_dict=rdc_attribute_dict)

            factors = generate_factors(spn_ensemble, query, first_spn, next_mergeable_relationships,
                                       next_mergeable_tables, rdc_spn_selection=True,
                                       rdc_attribute_dict=rdc_attribute_dict, merge_indicator_exp=True,
                                       exploit_incoming_multipliers=True, prefer_disjunct=False)

            factors = factor_refine(factors)

            parse_result = []
            
            for i, factor in enumerate(factors):
                if isinstance(factor, IndicatorExpectation):
                    assert isinstance(factor.spn, AQPSPN.aqp_spn.AQPSPN)
                    range_conditions = factor.spn._parse_conditions(factor.conditions, group_by_columns=None,
                                                                    group_by_tuples=None)
                    
                   
                    actual_query, fanout = prepare_single_query(range_conditions, factor)

                    parse_result.append({"bn_index": spn_ensemble.spns.index(factor.spn),
                                         "inverse": factor.inverse,
                                         "query": actual_query,
                                         "expectation": fanout,
                                         })
                    
                elif isinstance(factor, Expectation):
                    raise NotImplementedError
                else:
                    parse_result.append(factor)

            parsed_queries.append(parse_result)

        return parsed_queries, true_card

def parse_query_all(table_queries):
        res_table_queries = []
        for table_query in table_queries:
            res_table_query = []
            res_table_query.append(table_query[0])
            for i, query in enumerate(table_query[1:]):
                if type(query["bn_index"]) != int:
                    for j in self.bns:
                        if set(self.bns[j].table_name) == query["bn_index"]:
                            query["bn_index"] = j
                            break
                assert type(query["bn_index"]) == int, query["bn_index"]
                
            for i, query in enumerate(table_query[1:]):
                new_query = dict()
                ind = i+1
                if ind+1 < len(table_query):
                    if query["bn_index"] == table_query[ind+1]["bn_index"] and \
                        query["query"] == table_query[ind+1]["query"] and \
                            query["expectation"] == table_query[ind+1]["expectation"]:
                        continue
                if i > 0:
                    if query["bn_index"] == table_query[i]["bn_index"] and \
                        query["query"] == table_query[i]["query"] and \
                            query["expectation"] == table_query[i]["expectation"]:
                        continue
                new_query["bn_index"] = query["bn_index"]
                new_query["inverse"] = query["inverse"]
                new_query["expectation"] = query["expectation"]
                bn = self.bns[query["bn_index"]]
                new_query["query"], new_query["n_distinct"] = bn.query_decoding(query["query"])
                res_table_query.append(new_query)
            res_table_queries.append(res_table_query)
        return res_table_queries