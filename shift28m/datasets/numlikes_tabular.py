import os
import glob
import pickle
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split

from shift28m import constants as C
from shift28m import msgs as M
from shift28m.datasets import df_manipulations


class NumLikesRegression(object):
    def __init__(self, root: str = C.ROOT, load_jsonl: bool = False):
        if load_jsonl:
            # load *.jsonl files in the root directory
            self.jsonls: list = sorted(glob.glob(os.path.join(root, f"*.{C.JSONL}")))
            if len(self.jsonls) == 0:
                raise RuntimeError(M.DATASET_NOT_FOUND)

            self.df: pd.DataFrame = pd.read_json(
                self.jsonls[0], orient=C.RECORDS, lines=True
            )
            for jsonl in self.jsonls[1:]:
                df_: pd.DataFrame = pd.read_json(jsonl, orient=C.RECORDS, lines=True)
                self.df = pd.concat([self.df, df_])

            self.df: pd.DataFrame = self.df.sort_values(C.Keys.PUBLISH_DATE)

            self.__prepare_features()

            self.y: np.ndarray = np.array(self.df.like_num)
            self.x: np.ndarray = np.array(
                (
                    self.user_ids,
                    self.price_sum,
                    self.price_mean,
                    self.price_max,
                    self.price_min,
                )
            )

            self.x: np.ndarray = self.x.T
            self.x: np.ndarray = np.hstack([self.x, np.stack(self.category_ids_1)])
        else:
            # load *.pickle files in the root directory
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

    def __prepare_features(self):
        # generate input features
        self.user_ids: np.ndarray = (
            self.df[C.Keys.USER].map(df_manipulations.extract_user_id).values
        )
        self.price_sum: np.ndarray = (
            self.df[C.Keys.ITEMS].map(df_manipulations.price_sum).values
        )
        self.price_mean: np.ndarray = (
            self.df[C.Keys.ITEMS].map(df_manipulations.price_mean).values
        )
        self.price_max: np.ndarray = (
            self.df[C.Keys.ITEMS].map(df_manipulations.price_max).values
        )
        self.price_min: np.ndarray = (
            self.df[C.Keys.ITEMS].map(df_manipulations.price_min).values
        )
        self.category_ids_1: np.ndarray = (
            self.df[C.Keys.ITEMS]
            .map(df_manipulations.categories_count_embedding_id1)
            .to_numpy()
        )

    def load_dataset(
        self,
        train_size: int = 10000,
        test_size: int = 10000,
        target_shift: bool = False,
        train_mu: float = 50,
        train_sigma: float = 10,
        test_mu: float = 80,
        test_sigma: float = 10,
        random_seed: int = 128,
        max_iter: int = 100,
    ):

        N = len(self.x)
        if not target_shift:
            x_train, x_pool, y_train, y_pool = train_test_split(
                self.x, self.y, train_size=train_size, random_state=random_seed
            )
        else:
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

        return (x_train, y_train), (x_test, y_test)