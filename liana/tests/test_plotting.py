import numpy as np
from liana.plotting import dotplot, dotplot_by_sample, tileplot, interactions, contributions, target_metrics
from liana.testing import sample_lrs
from liana.testing import generate_toy_spatial

liana_res = sample_lrs()

def test_dotplot_order():
    my_p = dotplot(liana_res=liana_res,
                   size='specificity_rank',
                   colour='magnitude',
                   top_n=20,
                   orderby='specificity_rank',
                   orderby_ascending=False,
                   target_labels=["A", "B", "C"]
                   )
    assert my_p is not None
    assert 'interaction' in my_p.data.columns
    np.testing.assert_equal(np.unique(my_p.data.interaction).shape, (20,))
    set(my_p.data.target)
    assert {'A', 'B', 'C'} == set(my_p.data.target)


def test_doplot_filter():
    my_p2 = dotplot(liana_res=liana_res,
                    size='specificity_rank',
                    colour='magnitude',
                    filterby='specificity_rank',
                    filter_lambda=lambda x: x > 0.95,
                    inverse_colour=True,
                    source_labels=["A"]
                    )
    assert my_p2 is not None
    # we force this, but not intended all interactions
    # to be only 0.95, but rather for an interaction to get
    # plotted, in at least one cell type pair it should be > 0.95
    assert all(my_p2.data['specificity_rank'] > 0.95) is True


def test_dotplot_bysample():
    liana_res = sample_lrs(by_sample=True)
    my_p3 = dotplot_by_sample(liana_res=liana_res,
                              size='specificity_rank',
                              colour='magnitude',
                              target_labels='E',
                              sample_key='sample')
    assert my_p3 is not None
    assert 'interaction' in my_p3.data.columns
    assert 'sample' in my_p3.data.columns
    assert 'B' not in my_p3.data['target']
    

def test_tileplot():
    my_p2 = tileplot(liana_res = liana_res, 
                     # NOTE: fill & label need to exist for both
                     # ligand_ and receptor_ columns
                     fill='means',
                     label='pvals',
                     label_fun=lambda x: f'{x:.2f}',
                     top_n=10, 
                     orderby='specificity_rank',
                     orderby_ascending=True
                     )
    assert my_p2 is not None
    assert isinstance(my_p2.data['pvals'].values[0], str)


def test_proximity_plot():
    from liana.plotting import connectivity
    
    adata = generate_toy_spatial()
    my_p4 = connectivity(adata=adata, idx=0)
    assert my_p4 is not None


def test_target_metrics_plots():
    from liana.testing import _sample_target_metrics
    adata = generate_toy_spatial()
    adata.uns['target_metrics'] = _sample_target_metrics()
    adata.view_names = ['intra', 'extra']
    
    contributions(misty=adata, stat='intra_R2', top_n=1)
    target_metrics(misty=adata, stat='gain_R2')


def test_misty_interactions_plot():
    from liana.testing import _sample_interactions
    adata = generate_toy_spatial()
    adata.uns['interactions'] = _sample_interactions()
    adata.view_names = ['intra', 'extra']
    
    interactions(misty=adata, top_n=3, view='extra', key=lambda x: np.abs(x), ascending=False)
