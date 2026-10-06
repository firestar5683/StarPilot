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
void err_fun(double *nom_x, double *delta_x, double *out_247523503550074134) {
   out_247523503550074134[0] = delta_x[0] + nom_x[0];
   out_247523503550074134[1] = delta_x[1] + nom_x[1];
   out_247523503550074134[2] = delta_x[2] + nom_x[2];
   out_247523503550074134[3] = delta_x[3] + nom_x[3];
   out_247523503550074134[4] = delta_x[4] + nom_x[4];
   out_247523503550074134[5] = delta_x[5] + nom_x[5];
   out_247523503550074134[6] = delta_x[6] + nom_x[6];
   out_247523503550074134[7] = delta_x[7] + nom_x[7];
   out_247523503550074134[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_8641863619057206531) {
   out_8641863619057206531[0] = -nom_x[0] + true_x[0];
   out_8641863619057206531[1] = -nom_x[1] + true_x[1];
   out_8641863619057206531[2] = -nom_x[2] + true_x[2];
   out_8641863619057206531[3] = -nom_x[3] + true_x[3];
   out_8641863619057206531[4] = -nom_x[4] + true_x[4];
   out_8641863619057206531[5] = -nom_x[5] + true_x[5];
   out_8641863619057206531[6] = -nom_x[6] + true_x[6];
   out_8641863619057206531[7] = -nom_x[7] + true_x[7];
   out_8641863619057206531[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_8728310174040499930) {
   out_8728310174040499930[0] = 1.0;
   out_8728310174040499930[1] = 0.0;
   out_8728310174040499930[2] = 0.0;
   out_8728310174040499930[3] = 0.0;
   out_8728310174040499930[4] = 0.0;
   out_8728310174040499930[5] = 0.0;
   out_8728310174040499930[6] = 0.0;
   out_8728310174040499930[7] = 0.0;
   out_8728310174040499930[8] = 0.0;
   out_8728310174040499930[9] = 0.0;
   out_8728310174040499930[10] = 1.0;
   out_8728310174040499930[11] = 0.0;
   out_8728310174040499930[12] = 0.0;
   out_8728310174040499930[13] = 0.0;
   out_8728310174040499930[14] = 0.0;
   out_8728310174040499930[15] = 0.0;
   out_8728310174040499930[16] = 0.0;
   out_8728310174040499930[17] = 0.0;
   out_8728310174040499930[18] = 0.0;
   out_8728310174040499930[19] = 0.0;
   out_8728310174040499930[20] = 1.0;
   out_8728310174040499930[21] = 0.0;
   out_8728310174040499930[22] = 0.0;
   out_8728310174040499930[23] = 0.0;
   out_8728310174040499930[24] = 0.0;
   out_8728310174040499930[25] = 0.0;
   out_8728310174040499930[26] = 0.0;
   out_8728310174040499930[27] = 0.0;
   out_8728310174040499930[28] = 0.0;
   out_8728310174040499930[29] = 0.0;
   out_8728310174040499930[30] = 1.0;
   out_8728310174040499930[31] = 0.0;
   out_8728310174040499930[32] = 0.0;
   out_8728310174040499930[33] = 0.0;
   out_8728310174040499930[34] = 0.0;
   out_8728310174040499930[35] = 0.0;
   out_8728310174040499930[36] = 0.0;
   out_8728310174040499930[37] = 0.0;
   out_8728310174040499930[38] = 0.0;
   out_8728310174040499930[39] = 0.0;
   out_8728310174040499930[40] = 1.0;
   out_8728310174040499930[41] = 0.0;
   out_8728310174040499930[42] = 0.0;
   out_8728310174040499930[43] = 0.0;
   out_8728310174040499930[44] = 0.0;
   out_8728310174040499930[45] = 0.0;
   out_8728310174040499930[46] = 0.0;
   out_8728310174040499930[47] = 0.0;
   out_8728310174040499930[48] = 0.0;
   out_8728310174040499930[49] = 0.0;
   out_8728310174040499930[50] = 1.0;
   out_8728310174040499930[51] = 0.0;
   out_8728310174040499930[52] = 0.0;
   out_8728310174040499930[53] = 0.0;
   out_8728310174040499930[54] = 0.0;
   out_8728310174040499930[55] = 0.0;
   out_8728310174040499930[56] = 0.0;
   out_8728310174040499930[57] = 0.0;
   out_8728310174040499930[58] = 0.0;
   out_8728310174040499930[59] = 0.0;
   out_8728310174040499930[60] = 1.0;
   out_8728310174040499930[61] = 0.0;
   out_8728310174040499930[62] = 0.0;
   out_8728310174040499930[63] = 0.0;
   out_8728310174040499930[64] = 0.0;
   out_8728310174040499930[65] = 0.0;
   out_8728310174040499930[66] = 0.0;
   out_8728310174040499930[67] = 0.0;
   out_8728310174040499930[68] = 0.0;
   out_8728310174040499930[69] = 0.0;
   out_8728310174040499930[70] = 1.0;
   out_8728310174040499930[71] = 0.0;
   out_8728310174040499930[72] = 0.0;
   out_8728310174040499930[73] = 0.0;
   out_8728310174040499930[74] = 0.0;
   out_8728310174040499930[75] = 0.0;
   out_8728310174040499930[76] = 0.0;
   out_8728310174040499930[77] = 0.0;
   out_8728310174040499930[78] = 0.0;
   out_8728310174040499930[79] = 0.0;
   out_8728310174040499930[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_3958763527911310895) {
   out_3958763527911310895[0] = state[0];
   out_3958763527911310895[1] = state[1];
   out_3958763527911310895[2] = state[2];
   out_3958763527911310895[3] = state[3];
   out_3958763527911310895[4] = state[4];
   out_3958763527911310895[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_3958763527911310895[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_3958763527911310895[7] = state[7];
   out_3958763527911310895[8] = state[8];
}
void F_fun(double *state, double dt, double *out_5830504926638836462) {
   out_5830504926638836462[0] = 1;
   out_5830504926638836462[1] = 0;
   out_5830504926638836462[2] = 0;
   out_5830504926638836462[3] = 0;
   out_5830504926638836462[4] = 0;
   out_5830504926638836462[5] = 0;
   out_5830504926638836462[6] = 0;
   out_5830504926638836462[7] = 0;
   out_5830504926638836462[8] = 0;
   out_5830504926638836462[9] = 0;
   out_5830504926638836462[10] = 1;
   out_5830504926638836462[11] = 0;
   out_5830504926638836462[12] = 0;
   out_5830504926638836462[13] = 0;
   out_5830504926638836462[14] = 0;
   out_5830504926638836462[15] = 0;
   out_5830504926638836462[16] = 0;
   out_5830504926638836462[17] = 0;
   out_5830504926638836462[18] = 0;
   out_5830504926638836462[19] = 0;
   out_5830504926638836462[20] = 1;
   out_5830504926638836462[21] = 0;
   out_5830504926638836462[22] = 0;
   out_5830504926638836462[23] = 0;
   out_5830504926638836462[24] = 0;
   out_5830504926638836462[25] = 0;
   out_5830504926638836462[26] = 0;
   out_5830504926638836462[27] = 0;
   out_5830504926638836462[28] = 0;
   out_5830504926638836462[29] = 0;
   out_5830504926638836462[30] = 1;
   out_5830504926638836462[31] = 0;
   out_5830504926638836462[32] = 0;
   out_5830504926638836462[33] = 0;
   out_5830504926638836462[34] = 0;
   out_5830504926638836462[35] = 0;
   out_5830504926638836462[36] = 0;
   out_5830504926638836462[37] = 0;
   out_5830504926638836462[38] = 0;
   out_5830504926638836462[39] = 0;
   out_5830504926638836462[40] = 1;
   out_5830504926638836462[41] = 0;
   out_5830504926638836462[42] = 0;
   out_5830504926638836462[43] = 0;
   out_5830504926638836462[44] = 0;
   out_5830504926638836462[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_5830504926638836462[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_5830504926638836462[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_5830504926638836462[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_5830504926638836462[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_5830504926638836462[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_5830504926638836462[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_5830504926638836462[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_5830504926638836462[53] = -9.8100000000000005*dt;
   out_5830504926638836462[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_5830504926638836462[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_5830504926638836462[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_5830504926638836462[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_5830504926638836462[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_5830504926638836462[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_5830504926638836462[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_5830504926638836462[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_5830504926638836462[62] = 0;
   out_5830504926638836462[63] = 0;
   out_5830504926638836462[64] = 0;
   out_5830504926638836462[65] = 0;
   out_5830504926638836462[66] = 0;
   out_5830504926638836462[67] = 0;
   out_5830504926638836462[68] = 0;
   out_5830504926638836462[69] = 0;
   out_5830504926638836462[70] = 1;
   out_5830504926638836462[71] = 0;
   out_5830504926638836462[72] = 0;
   out_5830504926638836462[73] = 0;
   out_5830504926638836462[74] = 0;
   out_5830504926638836462[75] = 0;
   out_5830504926638836462[76] = 0;
   out_5830504926638836462[77] = 0;
   out_5830504926638836462[78] = 0;
   out_5830504926638836462[79] = 0;
   out_5830504926638836462[80] = 1;
}
void h_25(double *state, double *unused, double *out_8626650316087834658) {
   out_8626650316087834658[0] = state[6];
}
void H_25(double *state, double *unused, double *out_5205329524051008253) {
   out_5205329524051008253[0] = 0;
   out_5205329524051008253[1] = 0;
   out_5205329524051008253[2] = 0;
   out_5205329524051008253[3] = 0;
   out_5205329524051008253[4] = 0;
   out_5205329524051008253[5] = 0;
   out_5205329524051008253[6] = 1;
   out_5205329524051008253[7] = 0;
   out_5205329524051008253[8] = 0;
}
void h_24(double *state, double *unused, double *out_6473544106049484208) {
   out_6473544106049484208[0] = state[4];
   out_6473544106049484208[1] = state[5];
}
void H_24(double *state, double *unused, double *out_1647403925248685117) {
   out_1647403925248685117[0] = 0;
   out_1647403925248685117[1] = 0;
   out_1647403925248685117[2] = 0;
   out_1647403925248685117[3] = 0;
   out_1647403925248685117[4] = 1;
   out_1647403925248685117[5] = 0;
   out_1647403925248685117[6] = 0;
   out_1647403925248685117[7] = 0;
   out_1647403925248685117[8] = 0;
   out_1647403925248685117[9] = 0;
   out_1647403925248685117[10] = 0;
   out_1647403925248685117[11] = 0;
   out_1647403925248685117[12] = 0;
   out_1647403925248685117[13] = 0;
   out_1647403925248685117[14] = 1;
   out_1647403925248685117[15] = 0;
   out_1647403925248685117[16] = 0;
   out_1647403925248685117[17] = 0;
}
void h_30(double *state, double *unused, double *out_3906360730950968585) {
   out_3906360730950968585[0] = state[4];
}
void H_30(double *state, double *unused, double *out_2686996565543759626) {
   out_2686996565543759626[0] = 0;
   out_2686996565543759626[1] = 0;
   out_2686996565543759626[2] = 0;
   out_2686996565543759626[3] = 0;
   out_2686996565543759626[4] = 1;
   out_2686996565543759626[5] = 0;
   out_2686996565543759626[6] = 0;
   out_2686996565543759626[7] = 0;
   out_2686996565543759626[8] = 0;
}
void h_26(double *state, double *unused, double *out_8141341825344733885) {
   out_8141341825344733885[0] = state[7];
}
void H_26(double *state, double *unused, double *out_8946832842925064477) {
   out_8946832842925064477[0] = 0;
   out_8946832842925064477[1] = 0;
   out_8946832842925064477[2] = 0;
   out_8946832842925064477[3] = 0;
   out_8946832842925064477[4] = 0;
   out_8946832842925064477[5] = 0;
   out_8946832842925064477[6] = 0;
   out_8946832842925064477[7] = 1;
   out_8946832842925064477[8] = 0;
}
void h_27(double *state, double *unused, double *out_8023334431411357141) {
   out_8023334431411357141[0] = state[3];
}
void H_27(double *state, double *unused, double *out_463402494359816409) {
   out_463402494359816409[0] = 0;
   out_463402494359816409[1] = 0;
   out_463402494359816409[2] = 0;
   out_463402494359816409[3] = 1;
   out_463402494359816409[4] = 0;
   out_463402494359816409[5] = 0;
   out_463402494359816409[6] = 0;
   out_463402494359816409[7] = 0;
   out_463402494359816409[8] = 0;
}
void h_29(double *state, double *unused, double *out_3652574415947843539) {
   out_3652574415947843539[0] = state[1];
}
void H_29(double *state, double *unused, double *out_2176765221229367442) {
   out_2176765221229367442[0] = 0;
   out_2176765221229367442[1] = 1;
   out_2176765221229367442[2] = 0;
   out_2176765221229367442[3] = 0;
   out_2176765221229367442[4] = 0;
   out_2176765221229367442[5] = 0;
   out_2176765221229367442[6] = 0;
   out_2176765221229367442[7] = 0;
   out_2176765221229367442[8] = 0;
}
void h_28(double *state, double *unused, double *out_7819004321489496824) {
   out_7819004321489496824[0] = state[0];
}
void H_28(double *state, double *unused, double *out_7259164238298898016) {
   out_7259164238298898016[0] = 1;
   out_7259164238298898016[1] = 0;
   out_7259164238298898016[2] = 0;
   out_7259164238298898016[3] = 0;
   out_7259164238298898016[4] = 0;
   out_7259164238298898016[5] = 0;
   out_7259164238298898016[6] = 0;
   out_7259164238298898016[7] = 0;
   out_7259164238298898016[8] = 0;
}
void h_31(double *state, double *unused, double *out_5578923042988477975) {
   out_5578923042988477975[0] = state[8];
}
void H_31(double *state, double *unused, double *out_5174683562174047825) {
   out_5174683562174047825[0] = 0;
   out_5174683562174047825[1] = 0;
   out_5174683562174047825[2] = 0;
   out_5174683562174047825[3] = 0;
   out_5174683562174047825[4] = 0;
   out_5174683562174047825[5] = 0;
   out_5174683562174047825[6] = 0;
   out_5174683562174047825[7] = 0;
   out_5174683562174047825[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_247523503550074134) {
  err_fun(nom_x, delta_x, out_247523503550074134);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_8641863619057206531) {
  inv_err_fun(nom_x, true_x, out_8641863619057206531);
}
void car_H_mod_fun(double *state, double *out_8728310174040499930) {
  H_mod_fun(state, out_8728310174040499930);
}
void car_f_fun(double *state, double dt, double *out_3958763527911310895) {
  f_fun(state,  dt, out_3958763527911310895);
}
void car_F_fun(double *state, double dt, double *out_5830504926638836462) {
  F_fun(state,  dt, out_5830504926638836462);
}
void car_h_25(double *state, double *unused, double *out_8626650316087834658) {
  h_25(state, unused, out_8626650316087834658);
}
void car_H_25(double *state, double *unused, double *out_5205329524051008253) {
  H_25(state, unused, out_5205329524051008253);
}
void car_h_24(double *state, double *unused, double *out_6473544106049484208) {
  h_24(state, unused, out_6473544106049484208);
}
void car_H_24(double *state, double *unused, double *out_1647403925248685117) {
  H_24(state, unused, out_1647403925248685117);
}
void car_h_30(double *state, double *unused, double *out_3906360730950968585) {
  h_30(state, unused, out_3906360730950968585);
}
void car_H_30(double *state, double *unused, double *out_2686996565543759626) {
  H_30(state, unused, out_2686996565543759626);
}
void car_h_26(double *state, double *unused, double *out_8141341825344733885) {
  h_26(state, unused, out_8141341825344733885);
}
void car_H_26(double *state, double *unused, double *out_8946832842925064477) {
  H_26(state, unused, out_8946832842925064477);
}
void car_h_27(double *state, double *unused, double *out_8023334431411357141) {
  h_27(state, unused, out_8023334431411357141);
}
void car_H_27(double *state, double *unused, double *out_463402494359816409) {
  H_27(state, unused, out_463402494359816409);
}
void car_h_29(double *state, double *unused, double *out_3652574415947843539) {
  h_29(state, unused, out_3652574415947843539);
}
void car_H_29(double *state, double *unused, double *out_2176765221229367442) {
  H_29(state, unused, out_2176765221229367442);
}
void car_h_28(double *state, double *unused, double *out_7819004321489496824) {
  h_28(state, unused, out_7819004321489496824);
}
void car_H_28(double *state, double *unused, double *out_7259164238298898016) {
  H_28(state, unused, out_7259164238298898016);
}
void car_h_31(double *state, double *unused, double *out_5578923042988477975) {
  h_31(state, unused, out_5578923042988477975);
}
void car_H_31(double *state, double *unused, double *out_5174683562174047825) {
  H_31(state, unused, out_5174683562174047825);
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
