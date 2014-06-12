#include "mesh.h"
#include "cmeshToolsModule.h"
#include <apf.h>

class MeshAdaptPUMIDrvr{
 
  public:
  MeshAdaptPUMIDrvr(double, double, int); 
  ~MeshAdaptPUMIDrvr();

  Mesh mesh_proteus;
  int initProteusMesh(Mesh& mesh);

  int loadModelAndMesh(const char* modelFile, const char* meshFile);

  //Functions to construct proteus mesh data structures
  int ConstructFromSerialPUMIMesh(Mesh& mesh);
  int ConstructFromParallelPUMIMesh(Mesh& mesh, Mesh& subdomain_mesh);
 
  int UpdateMaterialArrays(Mesh& mesh, int bdryID, int GeomTag);

  //Fields
  int TransferSolutionToPUMI(double* inArray, int nVar, int nN);
  int TransferSolutionToProteus(double* outArray, int nVar, int nN);
  int CommuSizeField();
  int AdaptPUMIMesh();

  int CalculateSizeField(pMAdapt);
  int CalculateAnisoSizeField(apf::Field*);

  double hmax, hmin;
  int numIter;
  int nAdapt; //counter for number of adapt steps

  private: 
  apf::Mesh2* m;
  int comm_size, comm_rank;
  int elms_owned, faces_owned, edges_owned, vtx_owned;
  int numVar;

  apf::GlobalNumbering* global[4];
  apf::Numbering* local[4];
  apf::Field* solution;
  apf::Field* sizef;

  int ConstructGlobalNumbering(Mesh& mesh);
  int ConstructGlobalStructures(Mesh& mesh);

  int ConstructElements(Mesh& mesh);
  int ConstructNodes(Mesh& mesh);
  int ConstructBoundaries(Mesh& mesh);
  int ConstructEdges(Mesh& mesh);
  int ConstructMaterialArrays(Mesh& mesh);

  int SmoothField(apf::Field* f);
};
