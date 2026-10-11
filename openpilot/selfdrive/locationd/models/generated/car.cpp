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
void err_fun(double *nom_x, double *delta_x, double *out_8684748936880432144) {
   out_8684748936880432144[0] = delta_x[0] + nom_x[0];
   out_8684748936880432144[1] = delta_x[1] + nom_x[1];
   out_8684748936880432144[2] = delta_x[2] + nom_x[2];
   out_8684748936880432144[3] = delta_x[3] + nom_x[3];
   out_8684748936880432144[4] = delta_x[4] + nom_x[4];
   out_8684748936880432144[5] = delta_x[5] + nom_x[5];
   out_8684748936880432144[6] = delta_x[6] + nom_x[6];
   out_8684748936880432144[7] = delta_x[7] + nom_x[7];
   out_8684748936880432144[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_7066640499286813002) {
   out_7066640499286813002[0] = -nom_x[0] + true_x[0];
   out_7066640499286813002[1] = -nom_x[1] + true_x[1];
   out_7066640499286813002[2] = -nom_x[2] + true_x[2];
   out_7066640499286813002[3] = -nom_x[3] + true_x[3];
   out_7066640499286813002[4] = -nom_x[4] + true_x[4];
   out_7066640499286813002[5] = -nom_x[5] + true_x[5];
   out_7066640499286813002[6] = -nom_x[6] + true_x[6];
   out_7066640499286813002[7] = -nom_x[7] + true_x[7];
   out_7066640499286813002[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_3671072297043774273) {
   out_3671072297043774273[0] = 1.0;
   out_3671072297043774273[1] = 0.0;
   out_3671072297043774273[2] = 0.0;
   out_3671072297043774273[3] = 0.0;
   out_3671072297043774273[4] = 0.0;
   out_3671072297043774273[5] = 0.0;
   out_3671072297043774273[6] = 0.0;
   out_3671072297043774273[7] = 0.0;
   out_3671072297043774273[8] = 0.0;
   out_3671072297043774273[9] = 0.0;
   out_3671072297043774273[10] = 1.0;
   out_3671072297043774273[11] = 0.0;
   out_3671072297043774273[12] = 0.0;
   out_3671072297043774273[13] = 0.0;
   out_3671072297043774273[14] = 0.0;
   out_3671072297043774273[15] = 0.0;
   out_3671072297043774273[16] = 0.0;
   out_3671072297043774273[17] = 0.0;
   out_3671072297043774273[18] = 0.0;
   out_3671072297043774273[19] = 0.0;
   out_3671072297043774273[20] = 1.0;
   out_3671072297043774273[21] = 0.0;
   out_3671072297043774273[22] = 0.0;
   out_3671072297043774273[23] = 0.0;
   out_3671072297043774273[24] = 0.0;
   out_3671072297043774273[25] = 0.0;
   out_3671072297043774273[26] = 0.0;
   out_3671072297043774273[27] = 0.0;
   out_3671072297043774273[28] = 0.0;
   out_3671072297043774273[29] = 0.0;
   out_3671072297043774273[30] = 1.0;
   out_3671072297043774273[31] = 0.0;
   out_3671072297043774273[32] = 0.0;
   out_3671072297043774273[33] = 0.0;
   out_3671072297043774273[34] = 0.0;
   out_3671072297043774273[35] = 0.0;
   out_3671072297043774273[36] = 0.0;
   out_3671072297043774273[37] = 0.0;
   out_3671072297043774273[38] = 0.0;
   out_3671072297043774273[39] = 0.0;
   out_3671072297043774273[40] = 1.0;
   out_3671072297043774273[41] = 0.0;
   out_3671072297043774273[42] = 0.0;
   out_3671072297043774273[43] = 0.0;
   out_3671072297043774273[44] = 0.0;
   out_3671072297043774273[45] = 0.0;
   out_3671072297043774273[46] = 0.0;
   out_3671072297043774273[47] = 0.0;
   out_3671072297043774273[48] = 0.0;
   out_3671072297043774273[49] = 0.0;
   out_3671072297043774273[50] = 1.0;
   out_3671072297043774273[51] = 0.0;
   out_3671072297043774273[52] = 0.0;
   out_3671072297043774273[53] = 0.0;
   out_3671072297043774273[54] = 0.0;
   out_3671072297043774273[55] = 0.0;
   out_3671072297043774273[56] = 0.0;
   out_3671072297043774273[57] = 0.0;
   out_3671072297043774273[58] = 0.0;
   out_3671072297043774273[59] = 0.0;
   out_3671072297043774273[60] = 1.0;
   out_3671072297043774273[61] = 0.0;
   out_3671072297043774273[62] = 0.0;
   out_3671072297043774273[63] = 0.0;
   out_3671072297043774273[64] = 0.0;
   out_3671072297043774273[65] = 0.0;
   out_3671072297043774273[66] = 0.0;
   out_3671072297043774273[67] = 0.0;
   out_3671072297043774273[68] = 0.0;
   out_3671072297043774273[69] = 0.0;
   out_3671072297043774273[70] = 1.0;
   out_3671072297043774273[71] = 0.0;
   out_3671072297043774273[72] = 0.0;
   out_3671072297043774273[73] = 0.0;
   out_3671072297043774273[74] = 0.0;
   out_3671072297043774273[75] = 0.0;
   out_3671072297043774273[76] = 0.0;
   out_3671072297043774273[77] = 0.0;
   out_3671072297043774273[78] = 0.0;
   out_3671072297043774273[79] = 0.0;
   out_3671072297043774273[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_1095605561286512170) {
   out_1095605561286512170[0] = state[0];
   out_1095605561286512170[1] = state[1];
   out_1095605561286512170[2] = state[2];
   out_1095605561286512170[3] = state[3];
   out_1095605561286512170[4] = state[4];
   out_1095605561286512170[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_1095605561286512170[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_1095605561286512170[7] = state[7];
   out_1095605561286512170[8] = state[8];
}
void F_fun(double *state, double dt, double *out_5423923306597119811) {
   out_5423923306597119811[0] = 1;
   out_5423923306597119811[1] = 0;
   out_5423923306597119811[2] = 0;
   out_5423923306597119811[3] = 0;
   out_5423923306597119811[4] = 0;
   out_5423923306597119811[5] = 0;
   out_5423923306597119811[6] = 0;
   out_5423923306597119811[7] = 0;
   out_5423923306597119811[8] = 0;
   out_5423923306597119811[9] = 0;
   out_5423923306597119811[10] = 1;
   out_5423923306597119811[11] = 0;
   out_5423923306597119811[12] = 0;
   out_5423923306597119811[13] = 0;
   out_5423923306597119811[14] = 0;
   out_5423923306597119811[15] = 0;
   out_5423923306597119811[16] = 0;
   out_5423923306597119811[17] = 0;
   out_5423923306597119811[18] = 0;
   out_5423923306597119811[19] = 0;
   out_5423923306597119811[20] = 1;
   out_5423923306597119811[21] = 0;
   out_5423923306597119811[22] = 0;
   out_5423923306597119811[23] = 0;
   out_5423923306597119811[24] = 0;
   out_5423923306597119811[25] = 0;
   out_5423923306597119811[26] = 0;
   out_5423923306597119811[27] = 0;
   out_5423923306597119811[28] = 0;
   out_5423923306597119811[29] = 0;
   out_5423923306597119811[30] = 1;
   out_5423923306597119811[31] = 0;
   out_5423923306597119811[32] = 0;
   out_5423923306597119811[33] = 0;
   out_5423923306597119811[34] = 0;
   out_5423923306597119811[35] = 0;
   out_5423923306597119811[36] = 0;
   out_5423923306597119811[37] = 0;
   out_5423923306597119811[38] = 0;
   out_5423923306597119811[39] = 0;
   out_5423923306597119811[40] = 1;
   out_5423923306597119811[41] = 0;
   out_5423923306597119811[42] = 0;
   out_5423923306597119811[43] = 0;
   out_5423923306597119811[44] = 0;
   out_5423923306597119811[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_5423923306597119811[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_5423923306597119811[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_5423923306597119811[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_5423923306597119811[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_5423923306597119811[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_5423923306597119811[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_5423923306597119811[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_5423923306597119811[53] = -9.8100000000000005*dt;
   out_5423923306597119811[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_5423923306597119811[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_5423923306597119811[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_5423923306597119811[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_5423923306597119811[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_5423923306597119811[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_5423923306597119811[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_5423923306597119811[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_5423923306597119811[62] = 0;
   out_5423923306597119811[63] = 0;
   out_5423923306597119811[64] = 0;
   out_5423923306597119811[65] = 0;
   out_5423923306597119811[66] = 0;
   out_5423923306597119811[67] = 0;
   out_5423923306597119811[68] = 0;
   out_5423923306597119811[69] = 0;
   out_5423923306597119811[70] = 1;
   out_5423923306597119811[71] = 0;
   out_5423923306597119811[72] = 0;
   out_5423923306597119811[73] = 0;
   out_5423923306597119811[74] = 0;
   out_5423923306597119811[75] = 0;
   out_5423923306597119811[76] = 0;
   out_5423923306597119811[77] = 0;
   out_5423923306597119811[78] = 0;
   out_5423923306597119811[79] = 0;
   out_5423923306597119811[80] = 1;
}
void h_25(double *state, double *unused, double *out_4540217825902980379) {
   out_4540217825902980379[0] = state[6];
}
void H_25(double *state, double *unused, double *out_148091647054282596) {
   out_148091647054282596[0] = 0;
   out_148091647054282596[1] = 0;
   out_148091647054282596[2] = 0;
   out_148091647054282596[3] = 0;
   out_148091647054282596[4] = 0;
   out_148091647054282596[5] = 0;
   out_148091647054282596[6] = 1;
   out_148091647054282596[7] = 0;
   out_148091647054282596[8] = 0;
}
void h_24(double *state, double *unused, double *out_5565314556450199993) {
   out_5565314556450199993[0] = state[4];
   out_5565314556450199993[1] = state[5];
}
void H_24(double *state, double *unused, double *out_3409833951748040540) {
   out_3409833951748040540[0] = 0;
   out_3409833951748040540[1] = 0;
   out_3409833951748040540[2] = 0;
   out_3409833951748040540[3] = 0;
   out_3409833951748040540[4] = 1;
   out_3409833951748040540[5] = 0;
   out_3409833951748040540[6] = 0;
   out_3409833951748040540[7] = 0;
   out_3409833951748040540[8] = 0;
   out_3409833951748040540[9] = 0;
   out_3409833951748040540[10] = 0;
   out_3409833951748040540[11] = 0;
   out_3409833951748040540[12] = 0;
   out_3409833951748040540[13] = 0;
   out_3409833951748040540[14] = 1;
   out_3409833951748040540[15] = 0;
   out_3409833951748040540[16] = 0;
   out_3409833951748040540[17] = 0;
}
void h_30(double *state, double *unused, double *out_1626896214068153924) {
   out_1626896214068153924[0] = state[4];
}
void H_30(double *state, double *unused, double *out_4675787977181890794) {
   out_4675787977181890794[0] = 0;
   out_4675787977181890794[1] = 0;
   out_4675787977181890794[2] = 0;
   out_4675787977181890794[3] = 0;
   out_4675787977181890794[4] = 1;
   out_4675787977181890794[5] = 0;
   out_4675787977181890794[6] = 0;
   out_4675787977181890794[7] = 0;
   out_4675787977181890794[8] = 0;
}
void h_26(double *state, double *unused, double *out_3111249835438660006) {
   out_3111249835438660006[0] = state[7];
}
void H_26(double *state, double *unused, double *out_3889594965928338820) {
   out_3889594965928338820[0] = 0;
   out_3889594965928338820[1] = 0;
   out_3889594965928338820[2] = 0;
   out_3889594965928338820[3] = 0;
   out_3889594965928338820[4] = 0;
   out_3889594965928338820[5] = 0;
   out_3889594965928338820[6] = 0;
   out_3889594965928338820[7] = 1;
   out_3889594965928338820[8] = 0;
}
void h_27(double *state, double *unused, double *out_8904852980145725592) {
   out_8904852980145725592[0] = state[3];
}
void H_27(double *state, double *unused, double *out_2452193905997947577) {
   out_2452193905997947577[0] = 0;
   out_2452193905997947577[1] = 0;
   out_2452193905997947577[2] = 0;
   out_2452193905997947577[3] = 1;
   out_2452193905997947577[4] = 0;
   out_2452193905997947577[5] = 0;
   out_2452193905997947577[6] = 0;
   out_2452193905997947577[7] = 0;
   out_2452193905997947577[8] = 0;
}
void h_29(double *state, double *unused, double *out_5267403451891703242) {
   out_5267403451891703242[0] = state[1];
}
void H_29(double *state, double *unused, double *out_4165556632867498610) {
   out_4165556632867498610[0] = 0;
   out_4165556632867498610[1] = 1;
   out_4165556632867498610[2] = 0;
   out_4165556632867498610[3] = 0;
   out_4165556632867498610[4] = 0;
   out_4165556632867498610[5] = 0;
   out_4165556632867498610[6] = 0;
   out_4165556632867498610[7] = 0;
   out_4165556632867498610[8] = 0;
}
void h_28(double *state, double *unused, double *out_3903179712484879947) {
   out_3903179712484879947[0] = state[0];
}
void H_28(double *state, double *unused, double *out_2201926361302172359) {
   out_2201926361302172359[0] = 1;
   out_2201926361302172359[1] = 0;
   out_2201926361302172359[2] = 0;
   out_2201926361302172359[3] = 0;
   out_2201926361302172359[4] = 0;
   out_2201926361302172359[5] = 0;
   out_2201926361302172359[6] = 0;
   out_2201926361302172359[7] = 0;
   out_2201926361302172359[8] = 0;
}
void h_31(double *state, double *unused, double *out_5990849218531863546) {
   out_5990849218531863546[0] = state[8];
}
void H_31(double *state, double *unused, double *out_4515803068161690296) {
   out_4515803068161690296[0] = 0;
   out_4515803068161690296[1] = 0;
   out_4515803068161690296[2] = 0;
   out_4515803068161690296[3] = 0;
   out_4515803068161690296[4] = 0;
   out_4515803068161690296[5] = 0;
   out_4515803068161690296[6] = 0;
   out_4515803068161690296[7] = 0;
   out_4515803068161690296[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_8684748936880432144) {
  err_fun(nom_x, delta_x, out_8684748936880432144);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_7066640499286813002) {
  inv_err_fun(nom_x, true_x, out_7066640499286813002);
}
void car_H_mod_fun(double *state, double *out_3671072297043774273) {
  H_mod_fun(state, out_3671072297043774273);
}
void car_f_fun(double *state, double dt, double *out_1095605561286512170) {
  f_fun(state,  dt, out_1095605561286512170);
}
void car_F_fun(double *state, double dt, double *out_5423923306597119811) {
  F_fun(state,  dt, out_5423923306597119811);
}
void car_h_25(double *state, double *unused, double *out_4540217825902980379) {
  h_25(state, unused, out_4540217825902980379);
}
void car_H_25(double *state, double *unused, double *out_148091647054282596) {
  H_25(state, unused, out_148091647054282596);
}
void car_h_24(double *state, double *unused, double *out_5565314556450199993) {
  h_24(state, unused, out_5565314556450199993);
}
void car_H_24(double *state, double *unused, double *out_3409833951748040540) {
  H_24(state, unused, out_3409833951748040540);
}
void car_h_30(double *state, double *unused, double *out_1626896214068153924) {
  h_30(state, unused, out_1626896214068153924);
}
void car_H_30(double *state, double *unused, double *out_4675787977181890794) {
  H_30(state, unused, out_4675787977181890794);
}
void car_h_26(double *state, double *unused, double *out_3111249835438660006) {
  h_26(state, unused, out_3111249835438660006);
}
void car_H_26(double *state, double *unused, double *out_3889594965928338820) {
  H_26(state, unused, out_3889594965928338820);
}
void car_h_27(double *state, double *unused, double *out_8904852980145725592) {
  h_27(state, unused, out_8904852980145725592);
}
void car_H_27(double *state, double *unused, double *out_2452193905997947577) {
  H_27(state, unused, out_2452193905997947577);
}
void car_h_29(double *state, double *unused, double *out_5267403451891703242) {
  h_29(state, unused, out_5267403451891703242);
}
void car_H_29(double *state, double *unused, double *out_4165556632867498610) {
  H_29(state, unused, out_4165556632867498610);
}
void car_h_28(double *state, double *unused, double *out_3903179712484879947) {
  h_28(state, unused, out_3903179712484879947);
}
void car_H_28(double *state, double *unused, double *out_2201926361302172359) {
  H_28(state, unused, out_2201926361302172359);
}
void car_h_31(double *state, double *unused, double *out_5990849218531863546) {
  h_31(state, unused, out_5990849218531863546);
}
void car_H_31(double *state, double *unused, double *out_4515803068161690296) {
  H_31(state, unused, out_4515803068161690296);
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
