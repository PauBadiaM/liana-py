import os
import pathlib
import numpy as np
import scanpy as sc
from liana.method.sp._misty_constructs import lrMistyData, genericMistyData
from liana.testing._sample_anndata import generate_toy_spatial
from liana.method import MistyData

test_path = pathlib.Path(__file__).parent

adata = sc.read_h5ad(os.path.join(test_path, "data" , "synthetic.h5ad"))
adata = sc.pp.subsample(adata, n_obs=100, copy=True)


def test_misty_para():
    misty = genericMistyData(adata, bandwidth=10,
                             cutoff=0, add_juxta=False,
                             set_diag=False, seed=133)
    misty(bypass_intra=False, seed=42, n_estimators=11)
    assert np.isin(list(misty.uns.keys()), ['target_metrics', 'interactions']).all()
    target_metrics = misty.uns['target_metrics']
    # NOTE: contributions are not exactly equal to 1 per target per view
    # likely due to numpy rounding
    assert np.sum(target_metrics[['intra', 'para']].values, axis=1).sum() == 11.0
    assert target_metrics.shape == (11, 6)
    
    interactions = misty.uns['interactions']
    assert interactions.shape == (220, 4)
    assert interactions[interactions['target']=='ECM']['importances'].sum().round(8) == 2.0
    interaction_msk = (interactions['target']=='ligA') & \
        (interactions['predictor']=='protE')
    np.testing.assert_almost_equal(interactions[interaction_msk]['importances'].values,
                                np.array([0.0015018, 0.0732367]))
    np.testing.assert_almost_equal(target_metrics['gain_R2'].mean(), -0.0008262446448197796)
    

def test_misty_bypass():    
    misty = genericMistyData(adata, bandwidth=10, add_juxta=True, set_diag=True,
                             cutoff=0, coord_type="generic", delaunay=True)
    misty(alphas=1, bypass_intra=True, seed=42, n_estimators=11)
    assert np.isin(['juxta', 'para'], misty.uns['target_metrics'].columns).all()
    assert ~np.isin(['intra'], misty.uns['target_metrics'].columns).all()
    assert misty.uns['target_metrics'].shape == (11, 6)
    np.testing.assert_almost_equal(misty.uns['target_metrics']['multi_R2'].sum(), 0, decimal=5)
    
    interactions = misty.uns['interactions']
    assert interactions.shape == (220, 4)
    assert interactions['importances'].sum().round(10) == 22.0
    np.testing.assert_almost_equal(interactions[(interactions['target']=='ligC') &
                                               (interactions['predictor']=='ligA')]['importances'].values,
                                   np.array([0.0444664, 0.0541467]))
    

def test_misty_groups():
    misty = genericMistyData(adata,
                             bandwidth=20,
                             add_juxta=True, 
                             set_diag=False,
                             cutoff=0,
                             coord_type="generic",
                             delaunay=True
                             )
    misty(alphas=1, 
          bypass_intra=False,
          seed=42,
          predict_self=True, 
          maskby='cell_type',
          n_estimators=11)
    
    assert misty.uns['target_metrics'].shape==(22, 8)
    perf_actual = (misty.uns['target_metrics'].
     groupby(['intra_group'])['gain_R2'].
     mean().values
    )
    perf_expected = np.array([-0.0174493, -0.0121749])
    np.testing.assert_almost_equal(perf_actual, perf_expected)
    
    # assert that there are self interactions = var_n * var_n
    interactions = misty.uns['interactions']
    self_interactions = interactions[(interactions['target']==interactions['predictor'])]
    # 11 vars * 4 envs * 3 views = 132; NOTE: However, I drop NAs -> to be refactored...
    assert self_interactions.shape == (44, 5)
    assert self_interactions[self_interactions['view']=='intra']['importances'].isna().all()


def test_lr_misty():
    adata = generate_toy_spatial()
    misty = lrMistyData(adata, bandwidth=10, set_diag=True, cutoff=0)
    assert misty.shape == (700, 42)
    
    misty(n_estimators=10, bypass_intra=True)
    assert misty.uns['target_metrics'].shape == (16, 5)
    
    interactions = misty.uns['interactions']
    assert interactions.shape == (415, 4)
    cmplxs = interactions[interactions['target'].str.contains('_')]['target'].unique()
    assert np.isin(['CD8A_CD8B', 'CD74_CXCR4'], cmplxs).all()


def test_linear_misty():
    misty = genericMistyData(adata, bandwidth=10, set_diag=False, cutoff=0)
    assert misty.shape == (100, 33)
    
    misty(model='linear')
    assert misty.uns['target_metrics'].shape == (11, 7)
    np.testing.assert_almost_equal(misty.uns['target_metrics']['gain_R2'].sum(), -0.0647588938148182, decimal=3)
    
    assert misty.uns['interactions'].shape == (330, 4)
    actual = misty.uns['interactions']['importances'].values.mean()
    np.testing.assert_almost_equal(actual, 0.6683044, decimal=2)
    
    
def test_misty_mask():
    misty = genericMistyData(adata, bandwidth=10, set_diag=False, cutoff=0)
    misty = MistyData(misty)
    assert misty.shape == (100, 33)
    
    misty.mod['intra'].obs['mask'] = misty.mod['intra'].obs=='A'
    misty(model='linear', maskby='mask')
    
    assert misty.uns['target_metrics'].shape == (11, 7)
    np.testing.assert_almost_equal(misty.uns['target_metrics']['multi_R2'].mean(), 0.42037103778063667, decimal=3)
    np.testing.assert_almost_equal(misty.uns['target_metrics']['intra_R2'].mean(), 0.4248588250759459, decimal=3)
    
    assert misty.uns['interactions'].shape == (330, 4)
    np.testing.assert_almost_equal(misty.uns['interactions']['importances'].sum(), 184, decimal=0)
    

def test_misty_multivew():
    adata = generate_toy_spatial()
    # keep first 10 vars
    xdata = adata[:, :10].copy()
    xdata.var.index = 'x' + xdata.var.index
    
    ydata = adata[:, -10:].copy()
    ydata.var.index = 'y' + ydata.var.index
    intra = adata[:, 25:30].copy()
    misty = MistyData({'intra': intra, 'xdata': xdata, 'ydata': ydata}, verbose=True)
    misty(model='linear')
    
    misty.uns['interactions'].shape == (120, 4)
