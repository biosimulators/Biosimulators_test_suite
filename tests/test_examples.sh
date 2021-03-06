export REPORT_FORMATS=h5
export PLOT_FORMATS=
export BUNDLE_OUTPUTS=1
export KEEP_INDIVIDUAL_OUTPUTS=0

bionetgen -o examples/bngl/ -i examples/bngl/Dolan-PLoS-Comput-Biol-2015-NHEJ.omex
mv examples/bngl/reports.h5 examples/bngl/Dolan-PLoS-Comput-Biol-2015-NHEJ.h5

bionetgen -o examples/bngl/ -i examples/bngl/test-bngl.omex
mv examples/bngl/reports.h5 examples/bngl/test-bngl.h5

tellurium -o examples/sbml-core/ -i examples/sbml-core/Caravagna-J-Theor-Biol-2010-tumor-suppressive-oscillations.omex
mv examples/sbml-core/reports.h5 examples/sbml-core/Caravagna-J-Theor-Biol-2010-tumor-suppressive-oscillations.h5

tellurium -o examples/sbml-core/ -i examples/sbml-core/Ciliberto-J-Cell-Biol-2003-morphogenesis-checkpoint-discrete.omex
mv examples/sbml-core/reports.h5 examples/sbml-core/Ciliberto-J-Cell-Biol-2003-morphogenesis-checkpoint-discrete.h5

tellurium -o examples/sbml-core/ -i examples/sbml-core/Ciliberto-J-Cell-Biol-2003-morphogenesis-checkpoint-continuous.omex
mv examples/sbml-core/reports.h5 examples/sbml-core/Ciliberto-J-Cell-Biol-2003-morphogenesis-checkpoint-continuous.h5

pysces -o examples/sbml-core/ -i examples/sbml-core/Edelstein-Biol-Cybern-1996-Nicotinic-excitation.omex
mv examples/sbml-core/reports.h5 examples/sbml-core/Edelstein-Biol-Cybern-1996-Nicotinic-excitation.h5

tellurium -o examples/sbml-core/ -i examples/sbml-core/Parmar-BMC-Syst-Biol-2017-iron-distribution.omex
mv examples/sbml-core/reports.h5 examples/sbml-core/Parmar-BMC-Syst-Biol-2017-iron-distribution.h5

amici -o examples/sbml-core/ -i examples/sbml-core/Szymanska-J-Theor-Biol-2009-HSP-synthesis.omex
mv examples/sbml-core/reports.h5 examples/sbml-core/Szymanska-J-Theor-Biol-2009-HSP-synthesis.h5

copasi -o examples/sbml-core/ -i examples/sbml-core/Tomida-EMBO-J-2003-NFAT-translocation.omex
mv examples/sbml-core/reports.h5 examples/sbml-core/Tomida-EMBO-J-2003-NFAT-translocation.h5

copasi -o examples/sbml-core/ -i examples/sbml-core/Varusai-Sci-Rep-2018-mTOR-signaling-LSODA-LSODAR-SBML.omex
mv examples/sbml-core/reports.h5 examples/sbml-core/Varusai-Sci-Rep-2018-mTOR-signaling-LSODA-LSODAR-SBML.h5

cobrapy -o examples/sbml-fbc/ -i examples/sbml-fbc/Escherichia-coli-core-metabolism.omex
mv examples/sbml-fbc/reports.h5 examples/sbml-fbc/Escherichia-coli-core-metabolism.h5

boolnet -o examples/sbml-qual/ -i examples/sbml-qual/Chaouiya-BMC-Syst-Biol-2013-EGF-TNFa-signaling.omex
mv examples/sbml-qual/reports.h5 examples/sbml-qual/Chaouiya-BMC-Syst-Biol-2013-EGF-TNFa-signaling.h5

rm examples/bngl/log.yml
rm examples/sbml-core/log.yml
rm examples/sbml-fbc/log.yml
rm examples/sbml-qual/log.yml
