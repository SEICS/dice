import argparse
import logging
import os
import time
from dice_query_single_table import evaluate_single_table
from dice_query_imdb import evaluate_cardinality_imdb


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', default='dmv', help='Which dataset to be used')
    parser.add_argument('--gr', default='no', help='if applying graph reduction?')
    parser.add_argument('--bitwidth', default='no', help='compile syntax with bit width or with value?')
    # log level
    parser.add_argument('--log_level', type=int, default=logging.DEBUG)

    args = parser.parse_args()

    os.makedirs('logs', exist_ok=True)
    logging.basicConfig(
        level=args.log_level,
        # [%(threadName)-12.12s]
        format="%(asctime)s [%(levelname)-5.5s]  %(message)s",
        handlers=[
            logging.FileHandler("logs/{}_{}.log".format(args.dataset, time.strftime("%Y%m%d-%H%M%S"))),
            logging.StreamHandler()
        ])
    logger = logging.getLogger(__name__)

    #dealing with imdb job
    if args.dataset == 'imdb':
        if args.gr == 'yes' or args.gr == 'no':
            evaluate_cardinality_imdb(args.dataset, args.gr)
        else:
            print("Incorrect input. Please input yes or no.")
    elif args.dataset == 'census' or args.dataset == 'dmv':
        if args.gr == 'yes' or args.gr == 'no':
            evaluate_single_table(args.dataset, args.gr, args.bitwidth)
        else:
            print("Incorrect input. Please input yes or no.")
    else:
        print("Other datasets are not supported right now.")