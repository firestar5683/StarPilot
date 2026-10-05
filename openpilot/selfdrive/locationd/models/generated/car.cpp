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
void err_fun(double *nom_x, double *delta_x, double *out_7873944398687669040) {
   out_7873944398687669040[0] = delta_x[0] + nom_x[0];
   out_7873944398687669040[1] = delta_x[1] + nom_x[1];
   out_7873944398687669040[2] = delta_x[2] + nom_x[2];
   out_7873944398687669040[3] = delta_x[3] + nom_x[3];
   out_7873944398687669040[4] = delta_x[4] + nom_x[4];
   out_7873944398687669040[5] = delta_x[5] + nom_x[5];
   out_7873944398687669040[6] = delta_x[6] + nom_x[6];
   out_7873944398687669040[7] = delta_x[7] + nom_x[7];
   out_7873944398687669040[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_6410436380803709543) {
   out_6410436380803709543[0] = -nom_x[0] + true_x[0];
   out_6410436380803709543[1] = -nom_x[1] + true_x[1];
   out_6410436380803709543[2] = -nom_x[2] + true_x[2];
   out_6410436380803709543[3] = -nom_x[3] + true_x[3];
   out_6410436380803709543[4] = -nom_x[4] + true_x[4];
   out_6410436380803709543[5] = -nom_x[5] + true_x[5];
   out_6410436380803709543[6] = -nom_x[6] + true_x[6];
   out_6410436380803709543[7] = -nom_x[7] + true_x[7];
   out_6410436380803709543[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_1822083210648187229) {
   out_1822083210648187229[0] = 1.0;
   out_1822083210648187229[1] = 0.0;
   out_1822083210648187229[2] = 0.0;
   out_1822083210648187229[3] = 0.0;
   out_1822083210648187229[4] = 0.0;
   out_1822083210648187229[5] = 0.0;
   out_1822083210648187229[6] = 0.0;
   out_1822083210648187229[7] = 0.0;
   out_1822083210648187229[8] = 0.0;
   out_1822083210648187229[9] = 0.0;
   out_1822083210648187229[10] = 1.0;
   out_1822083210648187229[11] = 0.0;
   out_1822083210648187229[12] = 0.0;
   out_1822083210648187229[13] = 0.0;
   out_1822083210648187229[14] = 0.0;
   out_1822083210648187229[15] = 0.0;
   out_1822083210648187229[16] = 0.0;
   out_1822083210648187229[17] = 0.0;
   out_1822083210648187229[18] = 0.0;
   out_1822083210648187229[19] = 0.0;
   out_1822083210648187229[20] = 1.0;
   out_1822083210648187229[21] = 0.0;
   out_1822083210648187229[22] = 0.0;
   out_1822083210648187229[23] = 0.0;
   out_1822083210648187229[24] = 0.0;
   out_1822083210648187229[25] = 0.0;
   out_1822083210648187229[26] = 0.0;
   out_1822083210648187229[27] = 0.0;
   out_1822083210648187229[28] = 0.0;
   out_1822083210648187229[29] = 0.0;
   out_1822083210648187229[30] = 1.0;
   out_1822083210648187229[31] = 0.0;
   out_1822083210648187229[32] = 0.0;
   out_1822083210648187229[33] = 0.0;
   out_1822083210648187229[34] = 0.0;
   out_1822083210648187229[35] = 0.0;
   out_1822083210648187229[36] = 0.0;
   out_1822083210648187229[37] = 0.0;
   out_1822083210648187229[38] = 0.0;
   out_1822083210648187229[39] = 0.0;
   out_1822083210648187229[40] = 1.0;
   out_1822083210648187229[41] = 0.0;
   out_1822083210648187229[42] = 0.0;
   out_1822083210648187229[43] = 0.0;
   out_1822083210648187229[44] = 0.0;
   out_1822083210648187229[45] = 0.0;
   out_1822083210648187229[46] = 0.0;
   out_1822083210648187229[47] = 0.0;
   out_1822083210648187229[48] = 0.0;
   out_1822083210648187229[49] = 0.0;
   out_1822083210648187229[50] = 1.0;
   out_1822083210648187229[51] = 0.0;
   out_1822083210648187229[52] = 0.0;
   out_1822083210648187229[53] = 0.0;
   out_1822083210648187229[54] = 0.0;
   out_1822083210648187229[55] = 0.0;
   out_1822083210648187229[56] = 0.0;
   out_1822083210648187229[57] = 0.0;
   out_1822083210648187229[58] = 0.0;
   out_1822083210648187229[59] = 0.0;
   out_1822083210648187229[60] = 1.0;
   out_1822083210648187229[61] = 0.0;
   out_1822083210648187229[62] = 0.0;
   out_1822083210648187229[63] = 0.0;
   out_1822083210648187229[64] = 0.0;
   out_1822083210648187229[65] = 0.0;
   out_1822083210648187229[66] = 0.0;
   out_1822083210648187229[67] = 0.0;
   out_1822083210648187229[68] = 0.0;
   out_1822083210648187229[69] = 0.0;
   out_1822083210648187229[70] = 1.0;
   out_1822083210648187229[71] = 0.0;
   out_1822083210648187229[72] = 0.0;
   out_1822083210648187229[73] = 0.0;
   out_1822083210648187229[74] = 0.0;
   out_1822083210648187229[75] = 0.0;
   out_1822083210648187229[76] = 0.0;
   out_1822083210648187229[77] = 0.0;
   out_1822083210648187229[78] = 0.0;
   out_1822083210648187229[79] = 0.0;
   out_1822083210648187229[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_4879988995809842462) {
   out_4879988995809842462[0] = state[0];
   out_4879988995809842462[1] = state[1];
   out_4879988995809842462[2] = state[2];
   out_4879988995809842462[3] = state[3];
   out_4879988995809842462[4] = state[4];
   out_4879988995809842462[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_4879988995809842462[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_4879988995809842462[7] = state[7];
   out_4879988995809842462[8] = state[8];
}
void F_fun(double *state, double dt, double *out_7426947252524904028) {
   out_7426947252524904028[0] = 1;
   out_7426947252524904028[1] = 0;
   out_7426947252524904028[2] = 0;
   out_7426947252524904028[3] = 0;
   out_7426947252524904028[4] = 0;
   out_7426947252524904028[5] = 0;
   out_7426947252524904028[6] = 0;
   out_7426947252524904028[7] = 0;
   out_7426947252524904028[8] = 0;
   out_7426947252524904028[9] = 0;
   out_7426947252524904028[10] = 1;
   out_7426947252524904028[11] = 0;
   out_7426947252524904028[12] = 0;
   out_7426947252524904028[13] = 0;
   out_7426947252524904028[14] = 0;
   out_7426947252524904028[15] = 0;
   out_7426947252524904028[16] = 0;
   out_7426947252524904028[17] = 0;
   out_7426947252524904028[18] = 0;
   out_7426947252524904028[19] = 0;
   out_7426947252524904028[20] = 1;
   out_7426947252524904028[21] = 0;
   out_7426947252524904028[22] = 0;
   out_7426947252524904028[23] = 0;
   out_7426947252524904028[24] = 0;
   out_7426947252524904028[25] = 0;
   out_7426947252524904028[26] = 0;
   out_7426947252524904028[27] = 0;
   out_7426947252524904028[28] = 0;
   out_7426947252524904028[29] = 0;
   out_7426947252524904028[30] = 1;
   out_7426947252524904028[31] = 0;
   out_7426947252524904028[32] = 0;
   out_7426947252524904028[33] = 0;
   out_7426947252524904028[34] = 0;
   out_7426947252524904028[35] = 0;
   out_7426947252524904028[36] = 0;
   out_7426947252524904028[37] = 0;
   out_7426947252524904028[38] = 0;
   out_7426947252524904028[39] = 0;
   out_7426947252524904028[40] = 1;
   out_7426947252524904028[41] = 0;
   out_7426947252524904028[42] = 0;
   out_7426947252524904028[43] = 0;
   out_7426947252524904028[44] = 0;
   out_7426947252524904028[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_7426947252524904028[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_7426947252524904028[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_7426947252524904028[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_7426947252524904028[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_7426947252524904028[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_7426947252524904028[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_7426947252524904028[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_7426947252524904028[53] = -9.8100000000000005*dt;
   out_7426947252524904028[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_7426947252524904028[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_7426947252524904028[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_7426947252524904028[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_7426947252524904028[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_7426947252524904028[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_7426947252524904028[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_7426947252524904028[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_7426947252524904028[62] = 0;
   out_7426947252524904028[63] = 0;
   out_7426947252524904028[64] = 0;
   out_7426947252524904028[65] = 0;
   out_7426947252524904028[66] = 0;
   out_7426947252524904028[67] = 0;
   out_7426947252524904028[68] = 0;
   out_7426947252524904028[69] = 0;
   out_7426947252524904028[70] = 1;
   out_7426947252524904028[71] = 0;
   out_7426947252524904028[72] = 0;
   out_7426947252524904028[73] = 0;
   out_7426947252524904028[74] = 0;
   out_7426947252524904028[75] = 0;
   out_7426947252524904028[76] = 0;
   out_7426947252524904028[77] = 0;
   out_7426947252524904028[78] = 0;
   out_7426947252524904028[79] = 0;
   out_7426947252524904028[80] = 1;
}
void h_25(double *state, double *unused, double *out_7648063682542478630) {
   out_7648063682542478630[0] = state[6];
}
void H_25(double *state, double *unused, double *out_7860503003002095790) {
   out_7860503003002095790[0] = 0;
   out_7860503003002095790[1] = 0;
   out_7860503003002095790[2] = 0;
   out_7860503003002095790[3] = 0;
   out_7860503003002095790[4] = 0;
   out_7860503003002095790[5] = 0;
   out_7860503003002095790[6] = 1;
   out_7860503003002095790[7] = 0;
   out_7860503003002095790[8] = 0;
}
void h_24(double *state, double *unused, double *out_6113520950518082734) {
   out_6113520950518082734[0] = state[4];
   out_6113520950518082734[1] = state[5];
}
void H_24(double *state, double *unused, double *out_4302577404199772654) {
   out_4302577404199772654[0] = 0;
   out_4302577404199772654[1] = 0;
   out_4302577404199772654[2] = 0;
   out_4302577404199772654[3] = 0;
   out_4302577404199772654[4] = 1;
   out_4302577404199772654[5] = 0;
   out_4302577404199772654[6] = 0;
   out_4302577404199772654[7] = 0;
   out_4302577404199772654[8] = 0;
   out_4302577404199772654[9] = 0;
   out_4302577404199772654[10] = 0;
   out_4302577404199772654[11] = 0;
   out_4302577404199772654[12] = 0;
   out_4302577404199772654[13] = 0;
   out_4302577404199772654[14] = 1;
   out_4302577404199772654[15] = 0;
   out_4302577404199772654[16] = 0;
   out_4302577404199772654[17] = 0;
}
void h_30(double *state, double *unused, double *out_7923257744826984519) {
   out_7923257744826984519[0] = state[4];
}
void H_30(double *state, double *unused, double *out_5342170044494847163) {
   out_5342170044494847163[0] = 0;
   out_5342170044494847163[1] = 0;
   out_5342170044494847163[2] = 0;
   out_5342170044494847163[3] = 0;
   out_5342170044494847163[4] = 1;
   out_5342170044494847163[5] = 0;
   out_5342170044494847163[6] = 0;
   out_5342170044494847163[7] = 0;
   out_5342170044494847163[8] = 0;
}
void h_26(double *state, double *unused, double *out_7919081008073869446) {
   out_7919081008073869446[0] = state[7];
}
void H_26(double *state, double *unused, double *out_4555977033241295189) {
   out_4555977033241295189[0] = 0;
   out_4555977033241295189[1] = 0;
   out_4555977033241295189[2] = 0;
   out_4555977033241295189[3] = 0;
   out_4555977033241295189[4] = 0;
   out_4555977033241295189[5] = 0;
   out_4555977033241295189[6] = 0;
   out_4555977033241295189[7] = 1;
   out_4555977033241295189[8] = 0;
}
void h_27(double *state, double *unused, double *out_1249022165128629484) {
   out_1249022165128629484[0] = state[3];
}
void H_27(double *state, double *unused, double *out_7516933356295272074) {
   out_7516933356295272074[0] = 0;
   out_7516933356295272074[1] = 0;
   out_7516933356295272074[2] = 0;
   out_7516933356295272074[3] = 1;
   out_7516933356295272074[4] = 0;
   out_7516933356295272074[5] = 0;
   out_7516933356295272074[6] = 0;
   out_7516933356295272074[7] = 0;
   out_7516933356295272074[8] = 0;
}
void h_29(double *state, double *unused, double *out_4886471693382651834) {
   out_4886471693382651834[0] = state[1];
}
void H_29(double *state, double *unused, double *out_4831938700180454979) {
   out_4831938700180454979[0] = 0;
   out_4831938700180454979[1] = 1;
   out_4831938700180454979[2] = 0;
   out_4831938700180454979[3] = 0;
   out_4831938700180454979[4] = 0;
   out_4831938700180454979[5] = 0;
   out_4831938700180454979[6] = 0;
   out_4831938700180454979[7] = 0;
   out_4831938700180454979[8] = 0;
}
void h_28(double *state, double *unused, double *out_995235850125504438) {
   out_995235850125504438[0] = state[0];
}
void H_28(double *state, double *unused, double *out_8532406356459566063) {
   out_8532406356459566063[0] = 1;
   out_8532406356459566063[1] = 0;
   out_8532406356459566063[2] = 0;
   out_8532406356459566063[3] = 0;
   out_8532406356459566063[4] = 0;
   out_8532406356459566063[5] = 0;
   out_8532406356459566063[6] = 0;
   out_8532406356459566063[7] = 0;
   out_8532406356459566063[8] = 0;
}
void h_31(double *state, double *unused, double *out_6700377092887701122) {
   out_6700377092887701122[0] = state[8];
}
void H_31(double *state, double *unused, double *out_5182185135474646665) {
   out_5182185135474646665[0] = 0;
   out_5182185135474646665[1] = 0;
   out_5182185135474646665[2] = 0;
   out_5182185135474646665[3] = 0;
   out_5182185135474646665[4] = 0;
   out_5182185135474646665[5] = 0;
   out_5182185135474646665[6] = 0;
   out_5182185135474646665[7] = 0;
   out_5182185135474646665[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_7873944398687669040) {
  err_fun(nom_x, delta_x, out_7873944398687669040);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_6410436380803709543) {
  inv_err_fun(nom_x, true_x, out_6410436380803709543);
}
void car_H_mod_fun(double *state, double *out_1822083210648187229) {
  H_mod_fun(state, out_1822083210648187229);
}
void car_f_fun(double *state, double dt, double *out_4879988995809842462) {
  f_fun(state,  dt, out_4879988995809842462);
}
void car_F_fun(double *state, double dt, double *out_7426947252524904028) {
  F_fun(state,  dt, out_7426947252524904028);
}
void car_h_25(double *state, double *unused, double *out_7648063682542478630) {
  h_25(state, unused, out_7648063682542478630);
}
void car_H_25(double *state, double *unused, double *out_7860503003002095790) {
  H_25(state, unused, out_7860503003002095790);
}
void car_h_24(double *state, double *unused, double *out_6113520950518082734) {
  h_24(state, unused, out_6113520950518082734);
}
void car_H_24(double *state, double *unused, double *out_4302577404199772654) {
  H_24(state, unused, out_4302577404199772654);
}
void car_h_30(double *state, double *unused, double *out_7923257744826984519) {
  h_30(state, unused, out_7923257744826984519);
}
void car_H_30(double *state, double *unused, double *out_5342170044494847163) {
  H_30(state, unused, out_5342170044494847163);
}
void car_h_26(double *state, double *unused, double *out_7919081008073869446) {
  h_26(state, unused, out_7919081008073869446);
}
void car_H_26(double *state, double *unused, double *out_4555977033241295189) {
  H_26(state, unused, out_4555977033241295189);
}
void car_h_27(double *state, double *unused, double *out_1249022165128629484) {
  h_27(state, unused, out_1249022165128629484);
}
void car_H_27(double *state, double *unused, double *out_7516933356295272074) {
  H_27(state, unused, out_7516933356295272074);
}
void car_h_29(double *state, double *unused, double *out_4886471693382651834) {
  h_29(state, unused, out_4886471693382651834);
}
void car_H_29(double *state, double *unused, double *out_4831938700180454979) {
  H_29(state, unused, out_4831938700180454979);
}
void car_h_28(double *state, double *unused, double *out_995235850125504438) {
  h_28(state, unused, out_995235850125504438);
}
void car_H_28(double *state, double *unused, double *out_8532406356459566063) {
  H_28(state, unused, out_8532406356459566063);
}
void car_h_31(double *state, double *unused, double *out_6700377092887701122) {
  h_31(state, unused, out_6700377092887701122);
}
void car_H_31(double *state, double *unused, double *out_5182185135474646665) {
  H_31(state, unused, out_5182185135474646665);
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
