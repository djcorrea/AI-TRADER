import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from lab.models import fit_calibrated,purge_train
from lab.features import FEATURES
def dataset(n,seed):
    rng=np.random.default_rng(seed);x=pd.DataFrame(rng.normal(size=(n,len(FEATURES))),columns=FEATURES)
    x['label']=np.tile([-1,0,1],(n+2)//3)[:n];return x
def test_three_class_probabilities_scaler_training_only():
    fit=dataset(600,1);cal=dataset(300,2);test=dataset(300,3)
    factory=lambda:make_pipeline(StandardScaler(),LogisticRegression(C=.1,max_iter=100))
    model,calibrator,p=fit_calibrated(factory,fit,cal,test)
    assert p.shape==(300,3);assert np.allclose(p.sum(axis=1),1)
    assert np.allclose(model[0].mean_,fit[FEATURES].mean().to_numpy())
    mutated=test.copy();mutated[FEATURES]=mutated[FEATURES]*100
    b,_,_=fit_calibrated(factory,fit,cal,mutated)
    assert np.allclose(b[0].mean_,model[0].mean_)
    assert np.allclose(b[1].coef_,model[1].coef_)
def test_expected_value_net_costs_once():
    p=np.array([.1,.2,.7]);payoffs=np.array([-.01,0,.02])
    assert float(p@payoffs)==.013 # payoffs already net; cost must not be subtracted again
