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
void err_fun(double *nom_x, double *delta_x, double *out_4327500179553376114) {
   out_4327500179553376114[0] = delta_x[0] + nom_x[0];
   out_4327500179553376114[1] = delta_x[1] + nom_x[1];
   out_4327500179553376114[2] = delta_x[2] + nom_x[2];
   out_4327500179553376114[3] = delta_x[3] + nom_x[3];
   out_4327500179553376114[4] = delta_x[4] + nom_x[4];
   out_4327500179553376114[5] = delta_x[5] + nom_x[5];
   out_4327500179553376114[6] = delta_x[6] + nom_x[6];
   out_4327500179553376114[7] = delta_x[7] + nom_x[7];
   out_4327500179553376114[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_3590090955330921238) {
   out_3590090955330921238[0] = -nom_x[0] + true_x[0];
   out_3590090955330921238[1] = -nom_x[1] + true_x[1];
   out_3590090955330921238[2] = -nom_x[2] + true_x[2];
   out_3590090955330921238[3] = -nom_x[3] + true_x[3];
   out_3590090955330921238[4] = -nom_x[4] + true_x[4];
   out_3590090955330921238[5] = -nom_x[5] + true_x[5];
   out_3590090955330921238[6] = -nom_x[6] + true_x[6];
   out_3590090955330921238[7] = -nom_x[7] + true_x[7];
   out_3590090955330921238[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_2916657039326237022) {
   out_2916657039326237022[0] = 1.0;
   out_2916657039326237022[1] = 0.0;
   out_2916657039326237022[2] = 0.0;
   out_2916657039326237022[3] = 0.0;
   out_2916657039326237022[4] = 0.0;
   out_2916657039326237022[5] = 0.0;
   out_2916657039326237022[6] = 0.0;
   out_2916657039326237022[7] = 0.0;
   out_2916657039326237022[8] = 0.0;
   out_2916657039326237022[9] = 0.0;
   out_2916657039326237022[10] = 1.0;
   out_2916657039326237022[11] = 0.0;
   out_2916657039326237022[12] = 0.0;
   out_2916657039326237022[13] = 0.0;
   out_2916657039326237022[14] = 0.0;
   out_2916657039326237022[15] = 0.0;
   out_2916657039326237022[16] = 0.0;
   out_2916657039326237022[17] = 0.0;
   out_2916657039326237022[18] = 0.0;
   out_2916657039326237022[19] = 0.0;
   out_2916657039326237022[20] = 1.0;
   out_2916657039326237022[21] = 0.0;
   out_2916657039326237022[22] = 0.0;
   out_2916657039326237022[23] = 0.0;
   out_2916657039326237022[24] = 0.0;
   out_2916657039326237022[25] = 0.0;
   out_2916657039326237022[26] = 0.0;
   out_2916657039326237022[27] = 0.0;
   out_2916657039326237022[28] = 0.0;
   out_2916657039326237022[29] = 0.0;
   out_2916657039326237022[30] = 1.0;
   out_2916657039326237022[31] = 0.0;
   out_2916657039326237022[32] = 0.0;
   out_2916657039326237022[33] = 0.0;
   out_2916657039326237022[34] = 0.0;
   out_2916657039326237022[35] = 0.0;
   out_2916657039326237022[36] = 0.0;
   out_2916657039326237022[37] = 0.0;
   out_2916657039326237022[38] = 0.0;
   out_2916657039326237022[39] = 0.0;
   out_2916657039326237022[40] = 1.0;
   out_2916657039326237022[41] = 0.0;
   out_2916657039326237022[42] = 0.0;
   out_2916657039326237022[43] = 0.0;
   out_2916657039326237022[44] = 0.0;
   out_2916657039326237022[45] = 0.0;
   out_2916657039326237022[46] = 0.0;
   out_2916657039326237022[47] = 0.0;
   out_2916657039326237022[48] = 0.0;
   out_2916657039326237022[49] = 0.0;
   out_2916657039326237022[50] = 1.0;
   out_2916657039326237022[51] = 0.0;
   out_2916657039326237022[52] = 0.0;
   out_2916657039326237022[53] = 0.0;
   out_2916657039326237022[54] = 0.0;
   out_2916657039326237022[55] = 0.0;
   out_2916657039326237022[56] = 0.0;
   out_2916657039326237022[57] = 0.0;
   out_2916657039326237022[58] = 0.0;
   out_2916657039326237022[59] = 0.0;
   out_2916657039326237022[60] = 1.0;
   out_2916657039326237022[61] = 0.0;
   out_2916657039326237022[62] = 0.0;
   out_2916657039326237022[63] = 0.0;
   out_2916657039326237022[64] = 0.0;
   out_2916657039326237022[65] = 0.0;
   out_2916657039326237022[66] = 0.0;
   out_2916657039326237022[67] = 0.0;
   out_2916657039326237022[68] = 0.0;
   out_2916657039326237022[69] = 0.0;
   out_2916657039326237022[70] = 1.0;
   out_2916657039326237022[71] = 0.0;
   out_2916657039326237022[72] = 0.0;
   out_2916657039326237022[73] = 0.0;
   out_2916657039326237022[74] = 0.0;
   out_2916657039326237022[75] = 0.0;
   out_2916657039326237022[76] = 0.0;
   out_2916657039326237022[77] = 0.0;
   out_2916657039326237022[78] = 0.0;
   out_2916657039326237022[79] = 0.0;
   out_2916657039326237022[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_7982950417846647171) {
   out_7982950417846647171[0] = state[0];
   out_7982950417846647171[1] = state[1];
   out_7982950417846647171[2] = state[2];
   out_7982950417846647171[3] = state[3];
   out_7982950417846647171[4] = state[4];
   out_7982950417846647171[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_7982950417846647171[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_7982950417846647171[7] = state[7];
   out_7982950417846647171[8] = state[8];
}
void F_fun(double *state, double dt, double *out_1874021749855498275) {
   out_1874021749855498275[0] = 1;
   out_1874021749855498275[1] = 0;
   out_1874021749855498275[2] = 0;
   out_1874021749855498275[3] = 0;
   out_1874021749855498275[4] = 0;
   out_1874021749855498275[5] = 0;
   out_1874021749855498275[6] = 0;
   out_1874021749855498275[7] = 0;
   out_1874021749855498275[8] = 0;
   out_1874021749855498275[9] = 0;
   out_1874021749855498275[10] = 1;
   out_1874021749855498275[11] = 0;
   out_1874021749855498275[12] = 0;
   out_1874021749855498275[13] = 0;
   out_1874021749855498275[14] = 0;
   out_1874021749855498275[15] = 0;
   out_1874021749855498275[16] = 0;
   out_1874021749855498275[17] = 0;
   out_1874021749855498275[18] = 0;
   out_1874021749855498275[19] = 0;
   out_1874021749855498275[20] = 1;
   out_1874021749855498275[21] = 0;
   out_1874021749855498275[22] = 0;
   out_1874021749855498275[23] = 0;
   out_1874021749855498275[24] = 0;
   out_1874021749855498275[25] = 0;
   out_1874021749855498275[26] = 0;
   out_1874021749855498275[27] = 0;
   out_1874021749855498275[28] = 0;
   out_1874021749855498275[29] = 0;
   out_1874021749855498275[30] = 1;
   out_1874021749855498275[31] = 0;
   out_1874021749855498275[32] = 0;
   out_1874021749855498275[33] = 0;
   out_1874021749855498275[34] = 0;
   out_1874021749855498275[35] = 0;
   out_1874021749855498275[36] = 0;
   out_1874021749855498275[37] = 0;
   out_1874021749855498275[38] = 0;
   out_1874021749855498275[39] = 0;
   out_1874021749855498275[40] = 1;
   out_1874021749855498275[41] = 0;
   out_1874021749855498275[42] = 0;
   out_1874021749855498275[43] = 0;
   out_1874021749855498275[44] = 0;
   out_1874021749855498275[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_1874021749855498275[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_1874021749855498275[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_1874021749855498275[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_1874021749855498275[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_1874021749855498275[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_1874021749855498275[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_1874021749855498275[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_1874021749855498275[53] = -9.8100000000000005*dt;
   out_1874021749855498275[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_1874021749855498275[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_1874021749855498275[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_1874021749855498275[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_1874021749855498275[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_1874021749855498275[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_1874021749855498275[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_1874021749855498275[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_1874021749855498275[62] = 0;
   out_1874021749855498275[63] = 0;
   out_1874021749855498275[64] = 0;
   out_1874021749855498275[65] = 0;
   out_1874021749855498275[66] = 0;
   out_1874021749855498275[67] = 0;
   out_1874021749855498275[68] = 0;
   out_1874021749855498275[69] = 0;
   out_1874021749855498275[70] = 1;
   out_1874021749855498275[71] = 0;
   out_1874021749855498275[72] = 0;
   out_1874021749855498275[73] = 0;
   out_1874021749855498275[74] = 0;
   out_1874021749855498275[75] = 0;
   out_1874021749855498275[76] = 0;
   out_1874021749855498275[77] = 0;
   out_1874021749855498275[78] = 0;
   out_1874021749855498275[79] = 0;
   out_1874021749855498275[80] = 1;
}
void h_25(double *state, double *unused, double *out_6775859317196018453) {
   out_6775859317196018453[0] = state[6];
}
void H_25(double *state, double *unused, double *out_6439637689315728699) {
   out_6439637689315728699[0] = 0;
   out_6439637689315728699[1] = 0;
   out_6439637689315728699[2] = 0;
   out_6439637689315728699[3] = 0;
   out_6439637689315728699[4] = 0;
   out_6439637689315728699[5] = 0;
   out_6439637689315728699[6] = 1;
   out_6439637689315728699[7] = 0;
   out_6439637689315728699[8] = 0;
}
void h_24(double *state, double *unused, double *out_8888486471797321371) {
   out_8888486471797321371[0] = state[4];
   out_8888486471797321371[1] = state[5];
}
void H_24(double *state, double *unused, double *out_1619316184659740436) {
   out_1619316184659740436[0] = 0;
   out_1619316184659740436[1] = 0;
   out_1619316184659740436[2] = 0;
   out_1619316184659740436[3] = 0;
   out_1619316184659740436[4] = 1;
   out_1619316184659740436[5] = 0;
   out_1619316184659740436[6] = 0;
   out_1619316184659740436[7] = 0;
   out_1619316184659740436[8] = 0;
   out_1619316184659740436[9] = 0;
   out_1619316184659740436[10] = 0;
   out_1619316184659740436[11] = 0;
   out_1619316184659740436[12] = 0;
   out_1619316184659740436[13] = 0;
   out_1619316184659740436[14] = 1;
   out_1619316184659740436[15] = 0;
   out_1619316184659740436[16] = 0;
   out_1619316184659740436[17] = 0;
}
void h_30(double *state, double *unused, double *out_8976647325717484889) {
   out_8976647325717484889[0] = state[4];
}
void H_30(double *state, double *unused, double *out_6310298742172488629) {
   out_6310298742172488629[0] = 0;
   out_6310298742172488629[1] = 0;
   out_6310298742172488629[2] = 0;
   out_6310298742172488629[3] = 0;
   out_6310298742172488629[4] = 1;
   out_6310298742172488629[5] = 0;
   out_6310298742172488629[6] = 0;
   out_6310298742172488629[7] = 0;
   out_6310298742172488629[8] = 0;
}
void h_26(double *state, double *unused, double *out_948533943747329952) {
   out_948533943747329952[0] = state[7];
}
void H_26(double *state, double *unused, double *out_7096491753426040603) {
   out_7096491753426040603[0] = 0;
   out_7096491753426040603[1] = 0;
   out_7096491753426040603[2] = 0;
   out_7096491753426040603[3] = 0;
   out_7096491753426040603[4] = 0;
   out_7096491753426040603[5] = 0;
   out_7096491753426040603[6] = 0;
   out_7096491753426040603[7] = 1;
   out_7096491753426040603[8] = 0;
}
void h_27(double *state, double *unused, double *out_4171453996387320802) {
   out_4171453996387320802[0] = state[3];
}
void H_27(double *state, double *unused, double *out_4135535430372063718) {
   out_4135535430372063718[0] = 0;
   out_4135535430372063718[1] = 0;
   out_4135535430372063718[2] = 0;
   out_4135535430372063718[3] = 1;
   out_4135535430372063718[4] = 0;
   out_4135535430372063718[5] = 0;
   out_4135535430372063718[6] = 0;
   out_4135535430372063718[7] = 0;
   out_4135535430372063718[8] = 0;
}
void h_29(double *state, double *unused, double *out_4014267328036191657) {
   out_4014267328036191657[0] = state[1];
}
void H_29(double *state, double *unused, double *out_6820530086486880813) {
   out_6820530086486880813[0] = 0;
   out_6820530086486880813[1] = 1;
   out_6820530086486880813[2] = 0;
   out_6820530086486880813[3] = 0;
   out_6820530086486880813[4] = 0;
   out_6820530086486880813[5] = 0;
   out_6820530086486880813[6] = 0;
   out_6820530086486880813[7] = 0;
   out_6820530086486880813[8] = 0;
}
void h_28(double *state, double *unused, double *out_8361259295207794082) {
   out_8361259295207794082[0] = state[0];
}
void H_28(double *state, double *unused, double *out_1738131069417350239) {
   out_1738131069417350239[0] = 1;
   out_1738131069417350239[1] = 0;
   out_1738131069417350239[2] = 0;
   out_1738131069417350239[3] = 0;
   out_1738131069417350239[4] = 0;
   out_1738131069417350239[5] = 0;
   out_1738131069417350239[6] = 0;
   out_1738131069417350239[7] = 0;
   out_1738131069417350239[8] = 0;
}
void h_31(double *state, double *unused, double *out_1105413333558030732) {
   out_1105413333558030732[0] = state[8];
}
void H_31(double *state, double *unused, double *out_6470283651192689127) {
   out_6470283651192689127[0] = 0;
   out_6470283651192689127[1] = 0;
   out_6470283651192689127[2] = 0;
   out_6470283651192689127[3] = 0;
   out_6470283651192689127[4] = 0;
   out_6470283651192689127[5] = 0;
   out_6470283651192689127[6] = 0;
   out_6470283651192689127[7] = 0;
   out_6470283651192689127[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_4327500179553376114) {
  err_fun(nom_x, delta_x, out_4327500179553376114);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_3590090955330921238) {
  inv_err_fun(nom_x, true_x, out_3590090955330921238);
}
void car_H_mod_fun(double *state, double *out_2916657039326237022) {
  H_mod_fun(state, out_2916657039326237022);
}
void car_f_fun(double *state, double dt, double *out_7982950417846647171) {
  f_fun(state,  dt, out_7982950417846647171);
}
void car_F_fun(double *state, double dt, double *out_1874021749855498275) {
  F_fun(state,  dt, out_1874021749855498275);
}
void car_h_25(double *state, double *unused, double *out_6775859317196018453) {
  h_25(state, unused, out_6775859317196018453);
}
void car_H_25(double *state, double *unused, double *out_6439637689315728699) {
  H_25(state, unused, out_6439637689315728699);
}
void car_h_24(double *state, double *unused, double *out_8888486471797321371) {
  h_24(state, unused, out_8888486471797321371);
}
void car_H_24(double *state, double *unused, double *out_1619316184659740436) {
  H_24(state, unused, out_1619316184659740436);
}
void car_h_30(double *state, double *unused, double *out_8976647325717484889) {
  h_30(state, unused, out_8976647325717484889);
}
void car_H_30(double *state, double *unused, double *out_6310298742172488629) {
  H_30(state, unused, out_6310298742172488629);
}
void car_h_26(double *state, double *unused, double *out_948533943747329952) {
  h_26(state, unused, out_948533943747329952);
}
void car_H_26(double *state, double *unused, double *out_7096491753426040603) {
  H_26(state, unused, out_7096491753426040603);
}
void car_h_27(double *state, double *unused, double *out_4171453996387320802) {
  h_27(state, unused, out_4171453996387320802);
}
void car_H_27(double *state, double *unused, double *out_4135535430372063718) {
  H_27(state, unused, out_4135535430372063718);
}
void car_h_29(double *state, double *unused, double *out_4014267328036191657) {
  h_29(state, unused, out_4014267328036191657);
}
void car_H_29(double *state, double *unused, double *out_6820530086486880813) {
  H_29(state, unused, out_6820530086486880813);
}
void car_h_28(double *state, double *unused, double *out_8361259295207794082) {
  h_28(state, unused, out_8361259295207794082);
}
void car_H_28(double *state, double *unused, double *out_1738131069417350239) {
  H_28(state, unused, out_1738131069417350239);
}
void car_h_31(double *state, double *unused, double *out_1105413333558030732) {
  h_31(state, unused, out_1105413333558030732);
}
void car_H_31(double *state, double *unused, double *out_6470283651192689127) {
  H_31(state, unused, out_6470283651192689127);
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
