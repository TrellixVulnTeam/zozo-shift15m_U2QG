import os
import glob
import pickle
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split

from shift15m import constants as C
from shift15m import msgs as M
from shift15m.datasets import df_manipulations
from shift15m.datasets.base_dataset import BaseDataset


class SumPricesRegression(BaseDataset):
    def __init__(self, root: str = C.ROOT, load_jsonl: bool = False):
        if load_jsonl:
            # load *.jsonl files in the root directory
            self.__load_jsonl(root=root)
        else:
            root = os.path.join(root, C.Tasks.SUM_PRICES_REGRESSION)
            # load *.pickle files in the root directory
            self.__load_pickle(root=root)

    def __load_jsonl(self, root: str):
        self.jsonls: list = sorted(glob.glob(os.path.join(root, f"*.{C.JSONL}")))
        if len(self.jsonls) == 0:
            raise RuntimeError(M.DATASET_NOT_FOUND)

        self.df: pd.DataFrame = pd.read_json(
            self.jsonls[0], orient=C.RECORDS, lines=True
        )

        for jsonl in self.jsonls[1:]:
            df_: pd.DataFrame = pd.read_json(jsonl, orient=C.RECORDS, lines=True)
            self.df = pd.concat([self.df, df_])

        y = []
        items_list = self.df[C.Keys.ITEMS]
        for items in items_list:
            sum_prices = 0.0
            for item in items:
                sum_prices += float(item[C.Keys.PRICE])
            y.append(sum_prices)

        self.y: np.ndarray = np.array(y)
        self.x: np.ndarray = np.array(self.df.like_num)

    def __load_pickle(self, root: str):
        self.pickles: list = sorted(glob.glob(os.path.join(root, f"*.{C.PICKLE}")))
        if len(self.pickles) == 0:
            raise RuntimeError(M.DATASET_NOT_FOUND)

        with open(self.pickles[0], "rb") as f:
            (self.x, self.y) = pickle.load(f)

        for p in self.pickles[1:]:
            with open(p, "rb") as f:
                (x_, y_) = pickle.load(f)
                self.x = np.vstack([self.x, x_])
                self.y = np.hstack([self.y, y_])

    def load_dataset(
        self,
        train_size: int = 10000,
        test_size: int = 10000,
        covariate_shift: bool = False,
        target_shift: bool = False,
        train_mu: float = 50,
        train_sigma: float = 10,
        test_mu: float = 80,
        test_sigma: float = 10,
        random_seed: int = 128,
        max_iter: int = 100,
    ):

        if target_shift and covariate_shift:
            raise RuntimeError(M.INVALID_SHIFT_ARGUMENTS)

        N = len(self.x)
        if not target_shift and not covariate_shift:
            x_train, x_pool, y_train, y_pool = train_test_split(
                self.x, self.y, train_size=train_size, random_state=random_seed
            )
            _, x_test, _, y_test = train_test_split(
                x_pool, y_pool, test_size=test_size, random_state=random_seed
            )
        elif target_shift:
            np.random.seed(random_seed)
            ind = np.argsort(self.y).astype(np.uint32)
            x = self.x[ind]
            y = self.y[ind]

            test_ind_mu = np.searchsorted(y, test_mu)
            test_ind_sigma = test_ind_mu - np.searchsorted(y, test_mu - test_sigma)
            test_ind = np.random.normal(test_ind_mu, test_ind_sigma, test_size).astype(
                np.uint32
            )
            test_ind = np.delete(test_ind, np.where(test_ind >= len(y))[0], axis=0)

            x_test = x[test_ind]
            y_test = y[test_ind]

            x = np.delete(x, test_ind, axis=0)
            y = np.delete(y, test_ind, axis=0)

            train_ind_mu = np.searchsorted(y, train_mu)
            train_ind_sigma = train_ind_mu - np.searchsorted(y, train_mu - train_sigma)
            train_ind = np.random.normal(
                train_ind_mu, train_ind_sigma, train_size
            ).astype(np.uint32)
            train_ind = np.delete(train_ind, np.where(train_ind >= len(y))[0], axis=0)

            x_train = x[train_ind]
            y_train = y[train_ind]

        elif covariate_shift:
            np.random.seed(random_seed)
            ind = np.argsort(self.x).astype(np.uint32)
            x = self.x[ind]
            y = self.y[ind]

            test_ind_mu = np.searchsorted(x, test_mu)
            test_ind_sigma = test_ind_mu - np.searchsorted(x, test_mu - test_sigma)
            test_ind = np.random.normal(test_ind_mu, test_ind_sigma, test_size).astype(
                np.uint32
            )
            test_ind = np.delete(test_ind, np.where(test_ind >= len(y))[0], axis=0)

            x_test = x[test_ind]
            y_test = y[test_ind]

            x = np.delete(x, test_ind, axis=0)
            y = np.delete(y, test_ind, axis=0)

            train_ind_mu = np.searchsorted(x, train_mu)
            train_ind_sigma = train_ind_mu - np.searchsorted(x, train_mu - train_sigma)
            train_ind = np.random.normal(
                train_ind_mu, train_ind_sigma, train_size
            ).astype(np.uint32)
            train_ind = np.delete(train_ind, np.where(train_ind >= len(x))[0], axis=0)

            x_train = x[train_ind]
            y_train = y[train_ind]

        return (x_train, y_train), (x_test, y_test)