#include "car.h"

namespace {
#define DIM 9
#define EDIM 9
#define MEDIM 9
typedef void (*Hfun)(double *, double *, double *);

double mass;

void set_mass(double x){ mass = x;}

double rotational_inertia;

void set_rotational_inertia(double x){ rotational_inertia = x;}

double center_to_front;

void set_center_to_front(double x){ center_to_front = x;}

double center_to_rear;

void set_center_to_rear(double x){ center_to_rear = x;}

double stiffness_front;

void set_stiffness_front(double x){ stiffness_front = x;}

double stiffness_rear;

void set_stiffness_rear(double x){ stiffness_rear = x;}
const static double MAHA_THRESH_25 = 3.8414588206941227;
const static double MAHA_THRESH_24 = 5.991464547107981;
const static double MAHA_THRESH_30 = 3.8414588206941227;
const static double MAHA_THRESH_26 = 3.8414588206941227;
const static double MAHA_THRESH_27 = 3.8414588206941227;
const static double MAHA_THRESH_29 = 3.8414588206941227;
const static double MAHA_THRESH_28 = 3.8414588206941227;
const static double MAHA_THRESH_31 = 3.8414588206941227;

/******************************************************************************
 *                      Code generated with SymPy 1.14.0                      *
 *                                                                            *
 *              See http://www.sympy.org/ for more information.               *
 *                                                                            *
 *                         This file is part of 'ekf'                         *
 ******************************************************************************/
void err_fun(double *nom_x, double *delta_x, double *out_870685266903427678) {
   out_870685266903427678[0] = delta_x[0] + nom_x[0];
   out_870685266903427678[1] = delta_x[1] + nom_x[1];
   out_870685266903427678[2] = delta_x[2] + nom_x[2];
   out_870685266903427678[3] = delta_x[3] + nom_x[3];
   out_870685266903427678[4] = delta_x[4] + nom_x[4];
   out_870685266903427678[5] = delta_x[5] + nom_x[5];
   out_870685266903427678[6] = delta_x[6] + nom_x[6];
   out_870685266903427678[7] = delta_x[7] + nom_x[7];
   out_870685266903427678[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_8535551015639214025) {
   out_8535551015639214025[0] = -nom_x[0] + true_x[0];
   out_8535551015639214025[1] = -nom_x[1] + true_x[1];
   out_8535551015639214025[2] = -nom_x[2] + true_x[2];
   out_8535551015639214025[3] = -nom_x[3] + true_x[3];
   out_8535551015639214025[4] = -nom_x[4] + true_x[4];
   out_8535551015639214025[5] = -nom_x[5] + true_x[5];
   out_8535551015639214025[6] = -nom_x[6] + true_x[6];
   out_8535551015639214025[7] = -nom_x[7] + true_x[7];
   out_8535551015639214025[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_5722367516210042485) {
   out_5722367516210042485[0] = 1.0;
   out_5722367516210042485[1] = 0.0;
   out_5722367516210042485[2] = 0.0;
   out_5722367516210042485[3] = 0.0;
   out_5722367516210042485[4] = 0.0;
   out_5722367516210042485[5] = 0.0;
   out_5722367516210042485[6] = 0.0;
   out_5722367516210042485[7] = 0.0;
   out_5722367516210042485[8] = 0.0;
   out_5722367516210042485[9] = 0.0;
   out_5722367516210042485[10] = 1.0;
   out_5722367516210042485[11] = 0.0;
   out_5722367516210042485[12] = 0.0;
   out_5722367516210042485[13] = 0.0;
   out_5722367516210042485[14] = 0.0;
   out_5722367516210042485[15] = 0.0;
   out_5722367516210042485[16] = 0.0;
   out_5722367516210042485[17] = 0.0;
   out_5722367516210042485[18] = 0.0;
   out_5722367516210042485[19] = 0.0;
   out_5722367516210042485[20] = 1.0;
   out_5722367516210042485[21] = 0.0;
   out_5722367516210042485[22] = 0.0;
   out_5722367516210042485[23] = 0.0;
   out_5722367516210042485[24] = 0.0;
   out_5722367516210042485[25] = 0.0;
   out_5722367516210042485[26] = 0.0;
   out_5722367516210042485[27] = 0.0;
   out_5722367516210042485[28] = 0.0;
   out_5722367516210042485[29] = 0.0;
   out_5722367516210042485[30] = 1.0;
   out_5722367516210042485[31] = 0.0;
   out_5722367516210042485[32] = 0.0;
   out_5722367516210042485[33] = 0.0;
   out_5722367516210042485[34] = 0.0;
   out_5722367516210042485[35] = 0.0;
   out_5722367516210042485[36] = 0.0;
   out_5722367516210042485[37] = 0.0;
   out_5722367516210042485[38] = 0.0;
   out_5722367516210042485[39] = 0.0;
   out_5722367516210042485[40] = 1.0;
   out_5722367516210042485[41] = 0.0;
   out_5722367516210042485[42] = 0.0;
   out_5722367516210042485[43] = 0.0;
   out_5722367516210042485[44] = 0.0;
   out_5722367516210042485[45] = 0.0;
   out_5722367516210042485[46] = 0.0;
   out_5722367516210042485[47] = 0.0;
   out_5722367516210042485[48] = 0.0;
   out_5722367516210042485[49] = 0.0;
   out_5722367516210042485[50] = 1.0;
   out_5722367516210042485[51] = 0.0;
   out_5722367516210042485[52] = 0.0;
   out_5722367516210042485[53] = 0.0;
   out_5722367516210042485[54] = 0.0;
   out_5722367516210042485[55] = 0.0;
   out_5722367516210042485[56] = 0.0;
   out_5722367516210042485[57] = 0.0;
   out_5722367516210042485[58] = 0.0;
   out_5722367516210042485[59] = 0.0;
   out_5722367516210042485[60] = 1.0;
   out_5722367516210042485[61] = 0.0;
   out_5722367516210042485[62] = 0.0;
   out_5722367516210042485[63] = 0.0;
   out_5722367516210042485[64] = 0.0;
   out_5722367516210042485[65] = 0.0;
   out_5722367516210042485[66] = 0.0;
   out_5722367516210042485[67] = 0.0;
   out_5722367516210042485[68] = 0.0;
   out_5722367516210042485[69] = 0.0;
   out_5722367516210042485[70] = 1.0;
   out_5722367516210042485[71] = 0.0;
   out_5722367516210042485[72] = 0.0;
   out_5722367516210042485[73] = 0.0;
   out_5722367516210042485[74] = 0.0;
   out_5722367516210042485[75] = 0.0;
   out_5722367516210042485[76] = 0.0;
   out_5722367516210042485[77] = 0.0;
   out_5722367516210042485[78] = 0.0;
   out_5722367516210042485[79] = 0.0;
   out_5722367516210042485[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_6327711019370239094) {
   out_6327711019370239094[0] = state[0];
   out_6327711019370239094[1] = state[1];
   out_6327711019370239094[2] = state[2];
   out_6327711019370239094[3] = state[3];
   out_6327711019370239094[4] = state[4];
   out_6327711019370239094[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_6327711019370239094[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_6327711019370239094[7] = state[7];
   out_6327711019370239094[8] = state[8];
}
void F_fun(double *state, double dt, double *out_334732449615445707) {
   out_334732449615445707[0] = 1;
   out_334732449615445707[1] = 0;
   out_334732449615445707[2] = 0;
   out_334732449615445707[3] = 0;
   out_334732449615445707[4] = 0;
   out_334732449615445707[5] = 0;
   out_334732449615445707[6] = 0;
   out_334732449615445707[7] = 0;
   out_334732449615445707[8] = 0;
   out_334732449615445707[9] = 0;
   out_334732449615445707[10] = 1;
   out_334732449615445707[11] = 0;
   out_334732449615445707[12] = 0;
   out_334732449615445707[13] = 0;
   out_334732449615445707[14] = 0;
   out_334732449615445707[15] = 0;
   out_334732449615445707[16] = 0;
   out_334732449615445707[17] = 0;
   out_334732449615445707[18] = 0;
   out_334732449615445707[19] = 0;
   out_334732449615445707[20] = 1;
   out_334732449615445707[21] = 0;
   out_334732449615445707[22] = 0;
   out_334732449615445707[23] = 0;
   out_334732449615445707[24] = 0;
   out_334732449615445707[25] = 0;
   out_334732449615445707[26] = 0;
   out_334732449615445707[27] = 0;
   out_334732449615445707[28] = 0;
   out_334732449615445707[29] = 0;
   out_334732449615445707[30] = 1;
   out_334732449615445707[31] = 0;
   out_334732449615445707[32] = 0;
   out_334732449615445707[33] = 0;
   out_334732449615445707[34] = 0;
   out_334732449615445707[35] = 0;
   out_334732449615445707[36] = 0;
   out_334732449615445707[37] = 0;
   out_334732449615445707[38] = 0;
   out_334732449615445707[39] = 0;
   out_334732449615445707[40] = 1;
   out_334732449615445707[41] = 0;
   out_334732449615445707[42] = 0;
   out_334732449615445707[43] = 0;
   out_334732449615445707[44] = 0;
   out_334732449615445707[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_334732449615445707[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_334732449615445707[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_334732449615445707[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_334732449615445707[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_334732449615445707[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_334732449615445707[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_334732449615445707[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_334732449615445707[53] = -9.8100000000000005*dt;
   out_334732449615445707[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_334732449615445707[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_334732449615445707[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_334732449615445707[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_334732449615445707[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_334732449615445707[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_334732449615445707[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_334732449615445707[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_334732449615445707[62] = 0;
   out_334732449615445707[63] = 0;
   out_334732449615445707[64] = 0;
   out_334732449615445707[65] = 0;
   out_334732449615445707[66] = 0;
   out_334732449615445707[67] = 0;
   out_334732449615445707[68] = 0;
   out_334732449615445707[69] = 0;
   out_334732449615445707[70] = 1;
   out_334732449615445707[71] = 0;
   out_334732449615445707[72] = 0;
   out_334732449615445707[73] = 0;
   out_334732449615445707[74] = 0;
   out_334732449615445707[75] = 0;
   out_334732449615445707[76] = 0;
   out_334732449615445707[77] = 0;
   out_334732449615445707[78] = 0;
   out_334732449615445707[79] = 0;
   out_334732449615445707[80] = 1;
}
void h_25(double *state, double *unused, double *out_4988354507217303652) {
   out_4988354507217303652[0] = state[6];
}
void H_25(double *state, double *unused, double *out_3470820709702194752) {
   out_3470820709702194752[0] = 0;
   out_3470820709702194752[1] = 0;
   out_3470820709702194752[2] = 0;
   out_3470820709702194752[3] = 0;
   out_3470820709702194752[4] = 0;
   out_3470820709702194752[5] = 0;
   out_3470820709702194752[6] = 1;
   out_3470820709702194752[7] = 0;
   out_3470820709702194752[8] = 0;
}
void h_24(double *state, double *unused, double *out_8320591788748654668) {
   out_8320591788748654668[0] = state[4];
   out_8320591788748654668[1] = state[5];
}
void H_24(double *state, double *unused, double *out_5643470308707694318) {
   out_5643470308707694318[0] = 0;
   out_5643470308707694318[1] = 0;
   out_5643470308707694318[2] = 0;
   out_5643470308707694318[3] = 0;
   out_5643470308707694318[4] = 1;
   out_5643470308707694318[5] = 0;
   out_5643470308707694318[6] = 0;
   out_5643470308707694318[7] = 0;
   out_5643470308707694318[8] = 0;
   out_5643470308707694318[9] = 0;
   out_5643470308707694318[10] = 0;
   out_5643470308707694318[11] = 0;
   out_5643470308707694318[12] = 0;
   out_5643470308707694318[13] = 0;
   out_5643470308707694318[14] = 1;
   out_5643470308707694318[15] = 0;
   out_5643470308707694318[16] = 0;
   out_5643470308707694318[17] = 0;
}
void h_30(double *state, double *unused, double *out_6271436662034189635) {
   out_6271436662034189635[0] = state[4];
}
void H_30(double *state, double *unused, double *out_952487751194946125) {
   out_952487751194946125[0] = 0;
   out_952487751194946125[1] = 0;
   out_952487751194946125[2] = 0;
   out_952487751194946125[3] = 0;
   out_952487751194946125[4] = 1;
   out_952487751194946125[5] = 0;
   out_952487751194946125[6] = 0;
   out_952487751194946125[7] = 0;
   out_952487751194946125[8] = 0;
}
void h_26(double *state, double *unused, double *out_628706790953232800) {
   out_628706790953232800[0] = state[7];
}
void H_26(double *state, double *unused, double *out_7212324028576250976) {
   out_7212324028576250976[0] = 0;
   out_7212324028576250976[1] = 0;
   out_7212324028576250976[2] = 0;
   out_7212324028576250976[3] = 0;
   out_7212324028576250976[4] = 0;
   out_7212324028576250976[5] = 0;
   out_7212324028576250976[6] = 0;
   out_7212324028576250976[7] = 1;
   out_7212324028576250976[8] = 0;
}
void h_27(double *state, double *unused, double *out_7592759828026001303) {
   out_7592759828026001303[0] = state[3];
}
void H_27(double *state, double *unused, double *out_5774922968645859733) {
   out_5774922968645859733[0] = 0;
   out_5774922968645859733[1] = 0;
   out_5774922968645859733[2] = 0;
   out_5774922968645859733[3] = 1;
   out_5774922968645859733[4] = 0;
   out_5774922968645859733[5] = 0;
   out_5774922968645859733[6] = 0;
   out_5774922968645859733[7] = 0;
   out_5774922968645859733[8] = 0;
}
void h_29(double *state, double *unused, double *out_7749946496377130448) {
   out_7749946496377130448[0] = state[1];
}
void H_29(double *state, double *unused, double *out_7488285695515410766) {
   out_7488285695515410766[0] = 0;
   out_7488285695515410766[1] = 1;
   out_7488285695515410766[2] = 0;
   out_7488285695515410766[3] = 0;
   out_7488285695515410766[4] = 0;
   out_7488285695515410766[5] = 0;
   out_7488285695515410766[6] = 0;
   out_7488285695515410766[7] = 0;
   out_7488285695515410766[8] = 0;
}
void h_28(double *state, double *unused, double *out_1346308770565827835) {
   out_1346308770565827835[0] = state[0];
}
void H_28(double *state, double *unused, double *out_5524655423950084515) {
   out_5524655423950084515[0] = 1;
   out_5524655423950084515[1] = 0;
   out_5524655423950084515[2] = 0;
   out_5524655423950084515[3] = 0;
   out_5524655423950084515[4] = 0;
   out_5524655423950084515[5] = 0;
   out_5524655423950084515[6] = 0;
   out_5524655423950084515[7] = 0;
   out_5524655423950084515[8] = 0;
}
void h_31(double *state, double *unused, double *out_2214861449768682318) {
   out_2214861449768682318[0] = state[8];
}
void H_31(double *state, double *unused, double *out_7838532130809602452) {
   out_7838532130809602452[0] = 0;
   out_7838532130809602452[1] = 0;
   out_7838532130809602452[2] = 0;
   out_7838532130809602452[3] = 0;
   out_7838532130809602452[4] = 0;
   out_7838532130809602452[5] = 0;
   out_7838532130809602452[6] = 0;
   out_7838532130809602452[7] = 0;
   out_7838532130809602452[8] = 1;
}
#include <eigen3/Eigen/Dense>
#include <iostream>

typedef Eigen::Matrix<double, DIM, DIM, Eigen::RowMajor> DDM;
typedef Eigen::Matrix<double, EDIM, EDIM, Eigen::RowMajor> EEM;
typedef Eigen::Matrix<double, DIM, EDIM, Eigen::RowMajor> DEM;

void predict(double *in_x, double *in_P, double *in_Q, double dt) {
  typedef Eigen::Matrix<double, MEDIM, MEDIM, Eigen::RowMajor> RRM;

  double nx[DIM] = {0};
  double in_F[EDIM*EDIM] = {0};

  // functions from sympy
  f_fun(in_x, dt, nx);
  F_fun(in_x, dt, in_F);


  EEM F(in_F);
  EEM P(in_P);
  EEM Q(in_Q);

  RRM F_main = F.topLeftCorner(MEDIM, MEDIM);
  P.topLeftCorner(MEDIM, MEDIM) = (F_main * P.topLeftCorner(MEDIM, MEDIM)) * F_main.transpose();
  P.topRightCorner(MEDIM, EDIM - MEDIM) = F_main * P.topRightCorner(MEDIM, EDIM - MEDIM);
  P.bottomLeftCorner(EDIM - MEDIM, MEDIM) = P.bottomLeftCorner(EDIM - MEDIM, MEDIM) * F_main.transpose();

  P = P + dt*Q;

  // copy out state
  memcpy(in_x, nx, DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
}

// note: extra_args dim only correct when null space projecting
// otherwise 1
template <int ZDIM, int EADIM, bool MAHA_TEST>
void update(double *in_x, double *in_P, Hfun h_fun, Hfun H_fun, Hfun Hea_fun, double *in_z, double *in_R, double *in_ea, double MAHA_THRESHOLD) {
  typedef Eigen::Matrix<double, ZDIM, ZDIM, Eigen::RowMajor> ZZM;
  typedef Eigen::Matrix<double, ZDIM, DIM, Eigen::RowMajor> ZDM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, EDIM, Eigen::RowMajor> XEM;
  //typedef Eigen::Matrix<double, EDIM, ZDIM, Eigen::RowMajor> EZM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, 1> X1M;
  typedef Eigen::Matrix<double, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor> XXM;

  double in_hx[ZDIM] = {0};
  double in_H[ZDIM * DIM] = {0};
  double in_H_mod[EDIM * DIM] = {0};
  double delta_x[EDIM] = {0};
  double x_new[DIM] = {0};


  // state x, P
  Eigen::Matrix<double, ZDIM, 1> z(in_z);
  EEM P(in_P);
  ZZM pre_R(in_R);

  // functions from sympy
  h_fun(in_x, in_ea, in_hx);
  H_fun(in_x, in_ea, in_H);
  ZDM pre_H(in_H);

  // get y (y = z - hx)
  Eigen::Matrix<double, ZDIM, 1> pre_y(in_hx); pre_y = z - pre_y;
  X1M y; XXM H; XXM R;
  if (Hea_fun){
    typedef Eigen::Matrix<double, ZDIM, EADIM, Eigen::RowMajor> ZAM;
    double in_Hea[ZDIM * EADIM] = {0};
    Hea_fun(in_x, in_ea, in_Hea);
    ZAM Hea(in_Hea);
    XXM A = Hea.transpose().fullPivLu().kernel();


    y = A.transpose() * pre_y;
    H = A.transpose() * pre_H;
    R = A.transpose() * pre_R * A;
  } else {
    y = pre_y;
    H = pre_H;
    R = pre_R;
  }
  // get modified H
  H_mod_fun(in_x, in_H_mod);
  DEM H_mod(in_H_mod);
  XEM H_err = H * H_mod;

  // Do mahalobis distance test
  if (MAHA_TEST){
    XXM a = (H_err * P * H_err.transpose() + R).inverse();
    double maha_dist = y.transpose() * a * y;
    if (maha_dist > MAHA_THRESHOLD){
      R = 1.0e16 * R;
    }
  }

  // Outlier resilient weighting
  double weight = 1;//(1.5)/(1 + y.squaredNorm()/R.sum());

  // kalman gains and I_KH
  XXM S = ((H_err * P) * H_err.transpose()) + R/weight;
  XEM KT = S.fullPivLu().solve(H_err * P.transpose());
  //EZM K = KT.transpose(); TODO: WHY DOES THIS NOT COMPILE?
  //EZM K = S.fullPivLu().solve(H_err * P.transpose()).transpose();
  //std::cout << "Here is the matrix rot:\n" << K << std::endl;
  EEM I_KH = Eigen::Matrix<double, EDIM, EDIM>::Identity() - (KT.transpose() * H_err);

  // update state by injecting dx
  Eigen::Matrix<double, EDIM, 1> dx(delta_x);
  dx  = (KT.transpose() * y);
  memcpy(delta_x, dx.data(), EDIM * sizeof(double));
  err_fun(in_x, delta_x, x_new);
  Eigen::Matrix<double, DIM, 1> x(x_new);

  // update cov
  P = ((I_KH * P) * I_KH.transpose()) + ((KT.transpose() * R) * KT);

  // copy out state
  memcpy(in_x, x.data(), DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
  memcpy(in_z, y.data(), y.rows() * sizeof(double));
}




}
extern "C" {

void car_update_25(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_25, H_25, NULL, in_z, in_R, in_ea, MAHA_THRESH_25);
}
void car_update_24(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<2, 3, 0>(in_x, in_P, h_24, H_24, NULL, in_z, in_R, in_ea, MAHA_THRESH_24);
}
void car_update_30(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_30, H_30, NULL, in_z, in_R, in_ea, MAHA_THRESH_30);
}
void car_update_26(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_26, H_26, NULL, in_z, in_R, in_ea, MAHA_THRESH_26);
}
void car_update_27(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_27, H_27, NULL, in_z, in_R, in_ea, MAHA_THRESH_27);
}
void car_update_29(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_29, H_29, NULL, in_z, in_R, in_ea, MAHA_THRESH_29);
}
void car_update_28(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_28, H_28, NULL, in_z, in_R, in_ea, MAHA_THRESH_28);
}
void car_update_31(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_31, H_31, NULL, in_z, in_R, in_ea, MAHA_THRESH_31);
}
void car_err_fun(double *nom_x, double *delta_x, double *out_870685266903427678) {
  err_fun(nom_x, delta_x, out_870685266903427678);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_8535551015639214025) {
  inv_err_fun(nom_x, true_x, out_8535551015639214025);
}
void car_H_mod_fun(double *state, double *out_5722367516210042485) {
  H_mod_fun(state, out_5722367516210042485);
}
void car_f_fun(double *state, double dt, double *out_6327711019370239094) {
  f_fun(state,  dt, out_6327711019370239094);
}
void car_F_fun(double *state, double dt, double *out_334732449615445707) {
  F_fun(state,  dt, out_334732449615445707);
}
void car_h_25(double *state, double *unused, double *out_4988354507217303652) {
  h_25(state, unused, out_4988354507217303652);
}
void car_H_25(double *state, double *unused, double *out_3470820709702194752) {
  H_25(state, unused, out_3470820709702194752);
}
void car_h_24(double *state, double *unused, double *out_8320591788748654668) {
  h_24(state, unused, out_8320591788748654668);
}
void car_H_24(double *state, double *unused, double *out_5643470308707694318) {
  H_24(state, unused, out_5643470308707694318);
}
void car_h_30(double *state, double *unused, double *out_6271436662034189635) {
  h_30(state, unused, out_6271436662034189635);
}
void car_H_30(double *state, double *unused, double *out_952487751194946125) {
  H_30(state, unused, out_952487751194946125);
}
void car_h_26(double *state, double *unused, double *out_628706790953232800) {
  h_26(state, unused, out_628706790953232800);
}
void car_H_26(double *state, double *unused, double *out_7212324028576250976) {
  H_26(state, unused, out_7212324028576250976);
}
void car_h_27(double *state, double *unused, double *out_7592759828026001303) {
  h_27(state, unused, out_7592759828026001303);
}
void car_H_27(double *state, double *unused, double *out_5774922968645859733) {
  H_27(state, unused, out_5774922968645859733);
}
void car_h_29(double *state, double *unused, double *out_7749946496377130448) {
  h_29(state, unused, out_7749946496377130448);
}
void car_H_29(double *state, double *unused, double *out_7488285695515410766) {
  H_29(state, unused, out_7488285695515410766);
}
void car_h_28(double *state, double *unused, double *out_1346308770565827835) {
  h_28(state, unused, out_1346308770565827835);
}
void car_H_28(double *state, double *unused, double *out_5524655423950084515) {
  H_28(state, unused, out_5524655423950084515);
}
void car_h_31(double *state, double *unused, double *out_2214861449768682318) {
  h_31(state, unused, out_2214861449768682318);
}
void car_H_31(double *state, double *unused, double *out_7838532130809602452) {
  H_31(state, unused, out_7838532130809602452);
}
void car_predict(double *in_x, double *in_P, double *in_Q, double dt) {
  predict(in_x, in_P, in_Q, dt);
}
void car_set_mass(double x) {
  set_mass(x);
}
void car_set_rotational_inertia(double x) {
  set_rotational_inertia(x);
}
void car_set_center_to_front(double x) {
  set_center_to_front(x);
}
void car_set_center_to_rear(double x) {
  set_center_to_rear(x);
}
void car_set_stiffness_front(double x) {
  set_stiffness_front(x);
}
void car_set_stiffness_rear(double x) {
  set_stiffness_rear(x);
}
}

const EKF car = {
  .name = "car",
  .kinds = { 25, 24, 30, 26, 27, 29, 28, 31 },
  .feature_kinds = {  },
  .f_fun = car_f_fun,
  .F_fun = car_F_fun,
  .err_fun = car_err_fun,
  .inv_err_fun = car_inv_err_fun,
  .H_mod_fun = car_H_mod_fun,
  .predict = car_predict,
  .hs = {
    { 25, car_h_25 },
    { 24, car_h_24 },
    { 30, car_h_30 },
    { 26, car_h_26 },
    { 27, car_h_27 },
    { 29, car_h_29 },
    { 28, car_h_28 },
    { 31, car_h_31 },
  },
  .Hs = {
    { 25, car_H_25 },
    { 24, car_H_24 },
    { 30, car_H_30 },
    { 26, car_H_26 },
    { 27, car_H_27 },
    { 29, car_H_29 },
    { 28, car_H_28 },
    { 31, car_H_31 },
  },
  .updates = {
    { 25, car_update_25 },
    { 24, car_update_24 },
    { 30, car_update_30 },
    { 26, car_update_26 },
    { 27, car_update_27 },
    { 29, car_update_29 },
    { 28, car_update_28 },
    { 31, car_update_31 },
  },
  .Hes = {
  },
  .sets = {
    { "mass", car_set_mass },
    { "rotational_inertia", car_set_rotational_inertia },
    { "center_to_front", car_set_center_to_front },
    { "center_to_rear", car_set_center_to_rear },
    { "stiffness_front", car_set_stiffness_front },
    { "stiffness_rear", car_set_stiffness_rear },
  },
  .extra_routines = {
  },
};

ekf_lib_init(car)
