import numpy as np
from lab.paper import shadow_predict
from lab.features import FEATURES
class Model:
    def predict_proba(self,x):return np.repeat([[.1,.2,.7]],len(x),axis=0)
def test_shadow_inference_costs_already_net_and_no_orders():
    bundle={'model':Model(),'calibrator':Model(),'mu_negative':-.01,'mu_neutral':0.,'mu_positive':.02}
    result=shadow_predict(bundle,{k:0. for k in FEATURES})
    assert result['estimated_ev_net']==.013
    assert sum(result[k] for k in ['p_negative','p_no_opportunity','p_positive'])==1
    assert 'order' not in result and 'approved' not in result
