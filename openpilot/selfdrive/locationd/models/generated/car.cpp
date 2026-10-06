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
void err_fun(double *nom_x, double *delta_x, double *out_2719694004078796480) {
   out_2719694004078796480[0] = delta_x[0] + nom_x[0];
   out_2719694004078796480[1] = delta_x[1] + nom_x[1];
   out_2719694004078796480[2] = delta_x[2] + nom_x[2];
   out_2719694004078796480[3] = delta_x[3] + nom_x[3];
   out_2719694004078796480[4] = delta_x[4] + nom_x[4];
   out_2719694004078796480[5] = delta_x[5] + nom_x[5];
   out_2719694004078796480[6] = delta_x[6] + nom_x[6];
   out_2719694004078796480[7] = delta_x[7] + nom_x[7];
   out_2719694004078796480[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_856919065793812544) {
   out_856919065793812544[0] = -nom_x[0] + true_x[0];
   out_856919065793812544[1] = -nom_x[1] + true_x[1];
   out_856919065793812544[2] = -nom_x[2] + true_x[2];
   out_856919065793812544[3] = -nom_x[3] + true_x[3];
   out_856919065793812544[4] = -nom_x[4] + true_x[4];
   out_856919065793812544[5] = -nom_x[5] + true_x[5];
   out_856919065793812544[6] = -nom_x[6] + true_x[6];
   out_856919065793812544[7] = -nom_x[7] + true_x[7];
   out_856919065793812544[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_7350016175302370423) {
   out_7350016175302370423[0] = 1.0;
   out_7350016175302370423[1] = 0.0;
   out_7350016175302370423[2] = 0.0;
   out_7350016175302370423[3] = 0.0;
   out_7350016175302370423[4] = 0.0;
   out_7350016175302370423[5] = 0.0;
   out_7350016175302370423[6] = 0.0;
   out_7350016175302370423[7] = 0.0;
   out_7350016175302370423[8] = 0.0;
   out_7350016175302370423[9] = 0.0;
   out_7350016175302370423[10] = 1.0;
   out_7350016175302370423[11] = 0.0;
   out_7350016175302370423[12] = 0.0;
   out_7350016175302370423[13] = 0.0;
   out_7350016175302370423[14] = 0.0;
   out_7350016175302370423[15] = 0.0;
   out_7350016175302370423[16] = 0.0;
   out_7350016175302370423[17] = 0.0;
   out_7350016175302370423[18] = 0.0;
   out_7350016175302370423[19] = 0.0;
   out_7350016175302370423[20] = 1.0;
   out_7350016175302370423[21] = 0.0;
   out_7350016175302370423[22] = 0.0;
   out_7350016175302370423[23] = 0.0;
   out_7350016175302370423[24] = 0.0;
   out_7350016175302370423[25] = 0.0;
   out_7350016175302370423[26] = 0.0;
   out_7350016175302370423[27] = 0.0;
   out_7350016175302370423[28] = 0.0;
   out_7350016175302370423[29] = 0.0;
   out_7350016175302370423[30] = 1.0;
   out_7350016175302370423[31] = 0.0;
   out_7350016175302370423[32] = 0.0;
   out_7350016175302370423[33] = 0.0;
   out_7350016175302370423[34] = 0.0;
   out_7350016175302370423[35] = 0.0;
   out_7350016175302370423[36] = 0.0;
   out_7350016175302370423[37] = 0.0;
   out_7350016175302370423[38] = 0.0;
   out_7350016175302370423[39] = 0.0;
   out_7350016175302370423[40] = 1.0;
   out_7350016175302370423[41] = 0.0;
   out_7350016175302370423[42] = 0.0;
   out_7350016175302370423[43] = 0.0;
   out_7350016175302370423[44] = 0.0;
   out_7350016175302370423[45] = 0.0;
   out_7350016175302370423[46] = 0.0;
   out_7350016175302370423[47] = 0.0;
   out_7350016175302370423[48] = 0.0;
   out_7350016175302370423[49] = 0.0;
   out_7350016175302370423[50] = 1.0;
   out_7350016175302370423[51] = 0.0;
   out_7350016175302370423[52] = 0.0;
   out_7350016175302370423[53] = 0.0;
   out_7350016175302370423[54] = 0.0;
   out_7350016175302370423[55] = 0.0;
   out_7350016175302370423[56] = 0.0;
   out_7350016175302370423[57] = 0.0;
   out_7350016175302370423[58] = 0.0;
   out_7350016175302370423[59] = 0.0;
   out_7350016175302370423[60] = 1.0;
   out_7350016175302370423[61] = 0.0;
   out_7350016175302370423[62] = 0.0;
   out_7350016175302370423[63] = 0.0;
   out_7350016175302370423[64] = 0.0;
   out_7350016175302370423[65] = 0.0;
   out_7350016175302370423[66] = 0.0;
   out_7350016175302370423[67] = 0.0;
   out_7350016175302370423[68] = 0.0;
   out_7350016175302370423[69] = 0.0;
   out_7350016175302370423[70] = 1.0;
   out_7350016175302370423[71] = 0.0;
   out_7350016175302370423[72] = 0.0;
   out_7350016175302370423[73] = 0.0;
   out_7350016175302370423[74] = 0.0;
   out_7350016175302370423[75] = 0.0;
   out_7350016175302370423[76] = 0.0;
   out_7350016175302370423[77] = 0.0;
   out_7350016175302370423[78] = 0.0;
   out_7350016175302370423[79] = 0.0;
   out_7350016175302370423[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_6616197954711019157) {
   out_6616197954711019157[0] = state[0];
   out_6616197954711019157[1] = state[1];
   out_6616197954711019157[2] = state[2];
   out_6616197954711019157[3] = state[3];
   out_6616197954711019157[4] = state[4];
   out_6616197954711019157[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_6616197954711019157[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_6616197954711019157[7] = state[7];
   out_6616197954711019157[8] = state[8];
}
void F_fun(double *state, double dt, double *out_4925250846992883324) {
   out_4925250846992883324[0] = 1;
   out_4925250846992883324[1] = 0;
   out_4925250846992883324[2] = 0;
   out_4925250846992883324[3] = 0;
   out_4925250846992883324[4] = 0;
   out_4925250846992883324[5] = 0;
   out_4925250846992883324[6] = 0;
   out_4925250846992883324[7] = 0;
   out_4925250846992883324[8] = 0;
   out_4925250846992883324[9] = 0;
   out_4925250846992883324[10] = 1;
   out_4925250846992883324[11] = 0;
   out_4925250846992883324[12] = 0;
   out_4925250846992883324[13] = 0;
   out_4925250846992883324[14] = 0;
   out_4925250846992883324[15] = 0;
   out_4925250846992883324[16] = 0;
   out_4925250846992883324[17] = 0;
   out_4925250846992883324[18] = 0;
   out_4925250846992883324[19] = 0;
   out_4925250846992883324[20] = 1;
   out_4925250846992883324[21] = 0;
   out_4925250846992883324[22] = 0;
   out_4925250846992883324[23] = 0;
   out_4925250846992883324[24] = 0;
   out_4925250846992883324[25] = 0;
   out_4925250846992883324[26] = 0;
   out_4925250846992883324[27] = 0;
   out_4925250846992883324[28] = 0;
   out_4925250846992883324[29] = 0;
   out_4925250846992883324[30] = 1;
   out_4925250846992883324[31] = 0;
   out_4925250846992883324[32] = 0;
   out_4925250846992883324[33] = 0;
   out_4925250846992883324[34] = 0;
   out_4925250846992883324[35] = 0;
   out_4925250846992883324[36] = 0;
   out_4925250846992883324[37] = 0;
   out_4925250846992883324[38] = 0;
   out_4925250846992883324[39] = 0;
   out_4925250846992883324[40] = 1;
   out_4925250846992883324[41] = 0;
   out_4925250846992883324[42] = 0;
   out_4925250846992883324[43] = 0;
   out_4925250846992883324[44] = 0;
   out_4925250846992883324[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_4925250846992883324[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_4925250846992883324[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_4925250846992883324[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_4925250846992883324[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_4925250846992883324[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_4925250846992883324[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_4925250846992883324[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_4925250846992883324[53] = -9.8100000000000005*dt;
   out_4925250846992883324[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_4925250846992883324[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_4925250846992883324[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_4925250846992883324[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_4925250846992883324[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_4925250846992883324[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_4925250846992883324[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_4925250846992883324[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_4925250846992883324[62] = 0;
   out_4925250846992883324[63] = 0;
   out_4925250846992883324[64] = 0;
   out_4925250846992883324[65] = 0;
   out_4925250846992883324[66] = 0;
   out_4925250846992883324[67] = 0;
   out_4925250846992883324[68] = 0;
   out_4925250846992883324[69] = 0;
   out_4925250846992883324[70] = 1;
   out_4925250846992883324[71] = 0;
   out_4925250846992883324[72] = 0;
   out_4925250846992883324[73] = 0;
   out_4925250846992883324[74] = 0;
   out_4925250846992883324[75] = 0;
   out_4925250846992883324[76] = 0;
   out_4925250846992883324[77] = 0;
   out_4925250846992883324[78] = 0;
   out_4925250846992883324[79] = 0;
   out_4925250846992883324[80] = 1;
}
void h_25(double *state, double *unused, double *out_5036418257355363199) {
   out_5036418257355363199[0] = state[6];
}
void H_25(double *state, double *unused, double *out_3827035525312878746) {
   out_3827035525312878746[0] = 0;
   out_3827035525312878746[1] = 0;
   out_3827035525312878746[2] = 0;
   out_3827035525312878746[3] = 0;
   out_3827035525312878746[4] = 0;
   out_3827035525312878746[5] = 0;
   out_3827035525312878746[6] = 1;
   out_3827035525312878746[7] = 0;
   out_3827035525312878746[8] = 0;
}
void h_24(double *state, double *unused, double *out_1369846818760663587) {
   out_1369846818760663587[0] = state[4];
   out_1369846818760663587[1] = state[5];
}
void H_24(double *state, double *unused, double *out_2748536281278639355) {
   out_2748536281278639355[0] = 0;
   out_2748536281278639355[1] = 0;
   out_2748536281278639355[2] = 0;
   out_2748536281278639355[3] = 0;
   out_2748536281278639355[4] = 1;
   out_2748536281278639355[5] = 0;
   out_2748536281278639355[6] = 0;
   out_2748536281278639355[7] = 0;
   out_2748536281278639355[8] = 0;
   out_2748536281278639355[9] = 0;
   out_2748536281278639355[10] = 0;
   out_2748536281278639355[11] = 0;
   out_2748536281278639355[12] = 0;
   out_2748536281278639355[13] = 0;
   out_2748536281278639355[14] = 1;
   out_2748536281278639355[15] = 0;
   out_2748536281278639355[16] = 0;
   out_2748536281278639355[17] = 0;
}
void h_30(double *state, double *unused, double *out_5637836414968726753) {
   out_5637836414968726753[0] = state[4];
}
void H_30(double *state, double *unused, double *out_3089654816178738009) {
   out_3089654816178738009[0] = 0;
   out_3089654816178738009[1] = 0;
   out_3089654816178738009[2] = 0;
   out_3089654816178738009[3] = 0;
   out_3089654816178738009[4] = 1;
   out_3089654816178738009[5] = 0;
   out_3089654816178738009[6] = 0;
   out_3089654816178738009[7] = 0;
   out_3089654816178738009[8] = 0;
}
void h_26(double *state, double *unused, double *out_4551109766612262426) {
   out_4551109766612262426[0] = state[7];
}
void H_26(double *state, double *unused, double *out_7568538844186934970) {
   out_7568538844186934970[0] = 0;
   out_7568538844186934970[1] = 0;
   out_7568538844186934970[2] = 0;
   out_7568538844186934970[3] = 0;
   out_7568538844186934970[4] = 0;
   out_7568538844186934970[5] = 0;
   out_7568538844186934970[6] = 0;
   out_7568538844186934970[7] = 1;
   out_7568538844186934970[8] = 0;
}
void h_27(double *state, double *unused, double *out_34744989694517554) {
   out_34744989694517554[0] = state[3];
}
void H_27(double *state, double *unused, double *out_914891504378313098) {
   out_914891504378313098[0] = 0;
   out_914891504378313098[1] = 0;
   out_914891504378313098[2] = 0;
   out_914891504378313098[3] = 1;
   out_914891504378313098[4] = 0;
   out_914891504378313098[5] = 0;
   out_914891504378313098[6] = 0;
   out_914891504378313098[7] = 0;
   out_914891504378313098[8] = 0;
}
void h_29(double *state, double *unused, double *out_6553082936781777609) {
   out_6553082936781777609[0] = state[1];
}
void H_29(double *state, double *unused, double *out_3599886160493130193) {
   out_3599886160493130193[0] = 0;
   out_3599886160493130193[1] = 1;
   out_3599886160493130193[2] = 0;
   out_3599886160493130193[3] = 0;
   out_3599886160493130193[4] = 0;
   out_3599886160493130193[5] = 0;
   out_3599886160493130193[6] = 0;
   out_3599886160493130193[7] = 0;
   out_3599886160493130193[8] = 0;
}
void h_28(double *state, double *unused, double *out_4587441039761590760) {
   out_4587441039761590760[0] = state[0];
}
void H_28(double *state, double *unused, double *out_5880870239560768509) {
   out_5880870239560768509[0] = 1;
   out_5880870239560768509[1] = 0;
   out_5880870239560768509[2] = 0;
   out_5880870239560768509[3] = 0;
   out_5880870239560768509[4] = 0;
   out_5880870239560768509[5] = 0;
   out_5880870239560768509[6] = 0;
   out_5880870239560768509[7] = 0;
   out_5880870239560768509[8] = 0;
}
void h_31(double *state, double *unused, double *out_2726846999465309242) {
   out_2726846999465309242[0] = state[8];
}
void H_31(double *state, double *unused, double *out_3796389563435918318) {
   out_3796389563435918318[0] = 0;
   out_3796389563435918318[1] = 0;
   out_3796389563435918318[2] = 0;
   out_3796389563435918318[3] = 0;
   out_3796389563435918318[4] = 0;
   out_3796389563435918318[5] = 0;
   out_3796389563435918318[6] = 0;
   out_3796389563435918318[7] = 0;
   out_3796389563435918318[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_2719694004078796480) {
  err_fun(nom_x, delta_x, out_2719694004078796480);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_856919065793812544) {
  inv_err_fun(nom_x, true_x, out_856919065793812544);
}
void car_H_mod_fun(double *state, double *out_7350016175302370423) {
  H_mod_fun(state, out_7350016175302370423);
}
void car_f_fun(double *state, double dt, double *out_6616197954711019157) {
  f_fun(state,  dt, out_6616197954711019157);
}
void car_F_fun(double *state, double dt, double *out_4925250846992883324) {
  F_fun(state,  dt, out_4925250846992883324);
}
void car_h_25(double *state, double *unused, double *out_5036418257355363199) {
  h_25(state, unused, out_5036418257355363199);
}
void car_H_25(double *state, double *unused, double *out_3827035525312878746) {
  H_25(state, unused, out_3827035525312878746);
}
void car_h_24(double *state, double *unused, double *out_1369846818760663587) {
  h_24(state, unused, out_1369846818760663587);
}
void car_H_24(double *state, double *unused, double *out_2748536281278639355) {
  H_24(state, unused, out_2748536281278639355);
}
void car_h_30(double *state, double *unused, double *out_5637836414968726753) {
  h_30(state, unused, out_5637836414968726753);
}
void car_H_30(double *state, double *unused, double *out_3089654816178738009) {
  H_30(state, unused, out_3089654816178738009);
}
void car_h_26(double *state, double *unused, double *out_4551109766612262426) {
  h_26(state, unused, out_4551109766612262426);
}
void car_H_26(double *state, double *unused, double *out_7568538844186934970) {
  H_26(state, unused, out_7568538844186934970);
}
void car_h_27(double *state, double *unused, double *out_34744989694517554) {
  h_27(state, unused, out_34744989694517554);
}
void car_H_27(double *state, double *unused, double *out_914891504378313098) {
  H_27(state, unused, out_914891504378313098);
}
void car_h_29(double *state, double *unused, double *out_6553082936781777609) {
  h_29(state, unused, out_6553082936781777609);
}
void car_H_29(double *state, double *unused, double *out_3599886160493130193) {
  H_29(state, unused, out_3599886160493130193);
}
void car_h_28(double *state, double *unused, double *out_4587441039761590760) {
  h_28(state, unused, out_4587441039761590760);
}
void car_H_28(double *state, double *unused, double *out_5880870239560768509) {
  H_28(state, unused, out_5880870239560768509);
}
void car_h_31(double *state, double *unused, double *out_2726846999465309242) {
  h_31(state, unused, out_2726846999465309242);
}
void car_H_31(double *state, double *unused, double *out_3796389563435918318) {
  H_31(state, unused, out_3796389563435918318);
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
