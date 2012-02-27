${PROTEUS_PYTHON} ./config/configure.py --with-pic --with-clanguage=C --with-cc='mpicc -pthread' --with-cxx='mpicxx -pthread' --with-fc='mpif90 -pthread' --with-mpi-compilers --with-shared --with-dynamic --download-parmetis=ifneeded --download-spooles=ifneeded --download-superlu_dist=ifneeded --download-f-blas-lapack=ifneeded --prefix=${PROTEUS_PREFIX} \
--PETSC_ARCH=${PROTEUS_ARCH} \
--PETSC_DIR=${PROTEUS}/externalPackages/petsc

