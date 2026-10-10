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
void err_fun(double *nom_x, double *delta_x, double *out_4839724972372252268) {
   out_4839724972372252268[0] = delta_x[0] + nom_x[0];
   out_4839724972372252268[1] = delta_x[1] + nom_x[1];
   out_4839724972372252268[2] = delta_x[2] + nom_x[2];
   out_4839724972372252268[3] = delta_x[3] + nom_x[3];
   out_4839724972372252268[4] = delta_x[4] + nom_x[4];
   out_4839724972372252268[5] = delta_x[5] + nom_x[5];
   out_4839724972372252268[6] = delta_x[6] + nom_x[6];
   out_4839724972372252268[7] = delta_x[7] + nom_x[7];
   out_4839724972372252268[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_8829574174155035621) {
   out_8829574174155035621[0] = -nom_x[0] + true_x[0];
   out_8829574174155035621[1] = -nom_x[1] + true_x[1];
   out_8829574174155035621[2] = -nom_x[2] + true_x[2];
   out_8829574174155035621[3] = -nom_x[3] + true_x[3];
   out_8829574174155035621[4] = -nom_x[4] + true_x[4];
   out_8829574174155035621[5] = -nom_x[5] + true_x[5];
   out_8829574174155035621[6] = -nom_x[6] + true_x[6];
   out_8829574174155035621[7] = -nom_x[7] + true_x[7];
   out_8829574174155035621[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_8175464074684333633) {
   out_8175464074684333633[0] = 1.0;
   out_8175464074684333633[1] = 0.0;
   out_8175464074684333633[2] = 0.0;
   out_8175464074684333633[3] = 0.0;
   out_8175464074684333633[4] = 0.0;
   out_8175464074684333633[5] = 0.0;
   out_8175464074684333633[6] = 0.0;
   out_8175464074684333633[7] = 0.0;
   out_8175464074684333633[8] = 0.0;
   out_8175464074684333633[9] = 0.0;
   out_8175464074684333633[10] = 1.0;
   out_8175464074684333633[11] = 0.0;
   out_8175464074684333633[12] = 0.0;
   out_8175464074684333633[13] = 0.0;
   out_8175464074684333633[14] = 0.0;
   out_8175464074684333633[15] = 0.0;
   out_8175464074684333633[16] = 0.0;
   out_8175464074684333633[17] = 0.0;
   out_8175464074684333633[18] = 0.0;
   out_8175464074684333633[19] = 0.0;
   out_8175464074684333633[20] = 1.0;
   out_8175464074684333633[21] = 0.0;
   out_8175464074684333633[22] = 0.0;
   out_8175464074684333633[23] = 0.0;
   out_8175464074684333633[24] = 0.0;
   out_8175464074684333633[25] = 0.0;
   out_8175464074684333633[26] = 0.0;
   out_8175464074684333633[27] = 0.0;
   out_8175464074684333633[28] = 0.0;
   out_8175464074684333633[29] = 0.0;
   out_8175464074684333633[30] = 1.0;
   out_8175464074684333633[31] = 0.0;
   out_8175464074684333633[32] = 0.0;
   out_8175464074684333633[33] = 0.0;
   out_8175464074684333633[34] = 0.0;
   out_8175464074684333633[35] = 0.0;
   out_8175464074684333633[36] = 0.0;
   out_8175464074684333633[37] = 0.0;
   out_8175464074684333633[38] = 0.0;
   out_8175464074684333633[39] = 0.0;
   out_8175464074684333633[40] = 1.0;
   out_8175464074684333633[41] = 0.0;
   out_8175464074684333633[42] = 0.0;
   out_8175464074684333633[43] = 0.0;
   out_8175464074684333633[44] = 0.0;
   out_8175464074684333633[45] = 0.0;
   out_8175464074684333633[46] = 0.0;
   out_8175464074684333633[47] = 0.0;
   out_8175464074684333633[48] = 0.0;
   out_8175464074684333633[49] = 0.0;
   out_8175464074684333633[50] = 1.0;
   out_8175464074684333633[51] = 0.0;
   out_8175464074684333633[52] = 0.0;
   out_8175464074684333633[53] = 0.0;
   out_8175464074684333633[54] = 0.0;
   out_8175464074684333633[55] = 0.0;
   out_8175464074684333633[56] = 0.0;
   out_8175464074684333633[57] = 0.0;
   out_8175464074684333633[58] = 0.0;
   out_8175464074684333633[59] = 0.0;
   out_8175464074684333633[60] = 1.0;
   out_8175464074684333633[61] = 0.0;
   out_8175464074684333633[62] = 0.0;
   out_8175464074684333633[63] = 0.0;
   out_8175464074684333633[64] = 0.0;
   out_8175464074684333633[65] = 0.0;
   out_8175464074684333633[66] = 0.0;
   out_8175464074684333633[67] = 0.0;
   out_8175464074684333633[68] = 0.0;
   out_8175464074684333633[69] = 0.0;
   out_8175464074684333633[70] = 1.0;
   out_8175464074684333633[71] = 0.0;
   out_8175464074684333633[72] = 0.0;
   out_8175464074684333633[73] = 0.0;
   out_8175464074684333633[74] = 0.0;
   out_8175464074684333633[75] = 0.0;
   out_8175464074684333633[76] = 0.0;
   out_8175464074684333633[77] = 0.0;
   out_8175464074684333633[78] = 0.0;
   out_8175464074684333633[79] = 0.0;
   out_8175464074684333633[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_6716121585907694027) {
   out_6716121585907694027[0] = state[0];
   out_6716121585907694027[1] = state[1];
   out_6716121585907694027[2] = state[2];
   out_6716121585907694027[3] = state[3];
   out_6716121585907694027[4] = state[4];
   out_6716121585907694027[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_6716121585907694027[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_6716121585907694027[7] = state[7];
   out_6716121585907694027[8] = state[8];
}
void F_fun(double *state, double dt, double *out_3872222255603432155) {
   out_3872222255603432155[0] = 1;
   out_3872222255603432155[1] = 0;
   out_3872222255603432155[2] = 0;
   out_3872222255603432155[3] = 0;
   out_3872222255603432155[4] = 0;
   out_3872222255603432155[5] = 0;
   out_3872222255603432155[6] = 0;
   out_3872222255603432155[7] = 0;
   out_3872222255603432155[8] = 0;
   out_3872222255603432155[9] = 0;
   out_3872222255603432155[10] = 1;
   out_3872222255603432155[11] = 0;
   out_3872222255603432155[12] = 0;
   out_3872222255603432155[13] = 0;
   out_3872222255603432155[14] = 0;
   out_3872222255603432155[15] = 0;
   out_3872222255603432155[16] = 0;
   out_3872222255603432155[17] = 0;
   out_3872222255603432155[18] = 0;
   out_3872222255603432155[19] = 0;
   out_3872222255603432155[20] = 1;
   out_3872222255603432155[21] = 0;
   out_3872222255603432155[22] = 0;
   out_3872222255603432155[23] = 0;
   out_3872222255603432155[24] = 0;
   out_3872222255603432155[25] = 0;
   out_3872222255603432155[26] = 0;
   out_3872222255603432155[27] = 0;
   out_3872222255603432155[28] = 0;
   out_3872222255603432155[29] = 0;
   out_3872222255603432155[30] = 1;
   out_3872222255603432155[31] = 0;
   out_3872222255603432155[32] = 0;
   out_3872222255603432155[33] = 0;
   out_3872222255603432155[34] = 0;
   out_3872222255603432155[35] = 0;
   out_3872222255603432155[36] = 0;
   out_3872222255603432155[37] = 0;
   out_3872222255603432155[38] = 0;
   out_3872222255603432155[39] = 0;
   out_3872222255603432155[40] = 1;
   out_3872222255603432155[41] = 0;
   out_3872222255603432155[42] = 0;
   out_3872222255603432155[43] = 0;
   out_3872222255603432155[44] = 0;
   out_3872222255603432155[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_3872222255603432155[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_3872222255603432155[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_3872222255603432155[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_3872222255603432155[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_3872222255603432155[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_3872222255603432155[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_3872222255603432155[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_3872222255603432155[53] = -9.8100000000000005*dt;
   out_3872222255603432155[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_3872222255603432155[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_3872222255603432155[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_3872222255603432155[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_3872222255603432155[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_3872222255603432155[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_3872222255603432155[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_3872222255603432155[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_3872222255603432155[62] = 0;
   out_3872222255603432155[63] = 0;
   out_3872222255603432155[64] = 0;
   out_3872222255603432155[65] = 0;
   out_3872222255603432155[66] = 0;
   out_3872222255603432155[67] = 0;
   out_3872222255603432155[68] = 0;
   out_3872222255603432155[69] = 0;
   out_3872222255603432155[70] = 1;
   out_3872222255603432155[71] = 0;
   out_3872222255603432155[72] = 0;
   out_3872222255603432155[73] = 0;
   out_3872222255603432155[74] = 0;
   out_3872222255603432155[75] = 0;
   out_3872222255603432155[76] = 0;
   out_3872222255603432155[77] = 0;
   out_3872222255603432155[78] = 0;
   out_3872222255603432155[79] = 0;
   out_3872222255603432155[80] = 1;
}
void h_25(double *state, double *unused, double *out_2325222996689449646) {
   out_2325222996689449646[0] = state[6];
}
void H_25(double *state, double *unused, double *out_3271772249499668793) {
   out_3271772249499668793[0] = 0;
   out_3271772249499668793[1] = 0;
   out_3271772249499668793[2] = 0;
   out_3271772249499668793[3] = 0;
   out_3271772249499668793[4] = 0;
   out_3271772249499668793[5] = 0;
   out_3271772249499668793[6] = 1;
   out_3271772249499668793[7] = 0;
   out_3271772249499668793[8] = 0;
}
void h_24(double *state, double *unused, double *out_6848076894841716204) {
   out_6848076894841716204[0] = state[4];
   out_6848076894841716204[1] = state[5];
}
void H_24(double *state, double *unused, double *out_3303799557091849308) {
   out_3303799557091849308[0] = 0;
   out_3303799557091849308[1] = 0;
   out_3303799557091849308[2] = 0;
   out_3303799557091849308[3] = 0;
   out_3303799557091849308[4] = 1;
   out_3303799557091849308[5] = 0;
   out_3303799557091849308[6] = 0;
   out_3303799557091849308[7] = 0;
   out_3303799557091849308[8] = 0;
   out_3303799557091849308[9] = 0;
   out_3303799557091849308[10] = 0;
   out_3303799557091849308[11] = 0;
   out_3303799557091849308[12] = 0;
   out_3303799557091849308[13] = 0;
   out_3303799557091849308[14] = 1;
   out_3303799557091849308[15] = 0;
   out_3303799557091849308[16] = 0;
   out_3303799557091849308[17] = 0;
}
void h_30(double *state, double *unused, double *out_8228581582135578611) {
   out_8228581582135578611[0] = state[4];
}
void H_30(double *state, double *unused, double *out_3644918091991947962) {
   out_3644918091991947962[0] = 0;
   out_3644918091991947962[1] = 0;
   out_3644918091991947962[2] = 0;
   out_3644918091991947962[3] = 0;
   out_3644918091991947962[4] = 1;
   out_3644918091991947962[5] = 0;
   out_3644918091991947962[6] = 0;
   out_3644918091991947962[7] = 0;
   out_3644918091991947962[8] = 0;
}
void h_26(double *state, double *unused, double *out_7405610388304119622) {
   out_7405610388304119622[0] = state[7];
}
void H_26(double *state, double *unused, double *out_7013275568373725017) {
   out_7013275568373725017[0] = 0;
   out_7013275568373725017[1] = 0;
   out_7013275568373725017[2] = 0;
   out_7013275568373725017[3] = 0;
   out_7013275568373725017[4] = 0;
   out_7013275568373725017[5] = 0;
   out_7013275568373725017[6] = 0;
   out_7013275568373725017[7] = 1;
   out_7013275568373725017[8] = 0;
}
void h_27(double *state, double *unused, double *out_2676450270971395999) {
   out_2676450270971395999[0] = state[3];
}
void H_27(double *state, double *unused, double *out_5575874508443333774) {
   out_5575874508443333774[0] = 0;
   out_5575874508443333774[1] = 0;
   out_5575874508443333774[2] = 0;
   out_5575874508443333774[3] = 1;
   out_5575874508443333774[4] = 0;
   out_5575874508443333774[5] = 0;
   out_5575874508443333774[6] = 0;
   out_5575874508443333774[7] = 0;
   out_5575874508443333774[8] = 0;
}
void h_29(double *state, double *unused, double *out_1421853027307975865) {
   out_1421853027307975865[0] = state[1];
}
void H_29(double *state, double *unused, double *out_7289237235312884807) {
   out_7289237235312884807[0] = 0;
   out_7289237235312884807[1] = 1;
   out_7289237235312884807[2] = 0;
   out_7289237235312884807[3] = 0;
   out_7289237235312884807[4] = 0;
   out_7289237235312884807[5] = 0;
   out_7289237235312884807[6] = 0;
   out_7289237235312884807[7] = 0;
   out_7289237235312884807[8] = 0;
}
void h_28(double *state, double *unused, double *out_6305518901035444766) {
   out_6305518901035444766[0] = state[0];
}
void H_28(double *state, double *unused, double *out_5325606963747558556) {
   out_5325606963747558556[0] = 1;
   out_5325606963747558556[1] = 0;
   out_5325606963747558556[2] = 0;
   out_5325606963747558556[3] = 0;
   out_5325606963747558556[4] = 0;
   out_5325606963747558556[5] = 0;
   out_5325606963747558556[6] = 0;
   out_5325606963747558556[7] = 0;
   out_5325606963747558556[8] = 0;
}
void h_31(double *state, double *unused, double *out_2600417058973955535) {
   out_2600417058973955535[0] = state[8];
}
void H_31(double *state, double *unused, double *out_3241126287622708365) {
   out_3241126287622708365[0] = 0;
   out_3241126287622708365[1] = 0;
   out_3241126287622708365[2] = 0;
   out_3241126287622708365[3] = 0;
   out_3241126287622708365[4] = 0;
   out_3241126287622708365[5] = 0;
   out_3241126287622708365[6] = 0;
   out_3241126287622708365[7] = 0;
   out_3241126287622708365[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_4839724972372252268) {
  err_fun(nom_x, delta_x, out_4839724972372252268);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_8829574174155035621) {
  inv_err_fun(nom_x, true_x, out_8829574174155035621);
}
void car_H_mod_fun(double *state, double *out_8175464074684333633) {
  H_mod_fun(state, out_8175464074684333633);
}
void car_f_fun(double *state, double dt, double *out_6716121585907694027) {
  f_fun(state,  dt, out_6716121585907694027);
}
void car_F_fun(double *state, double dt, double *out_3872222255603432155) {
  F_fun(state,  dt, out_3872222255603432155);
}
void car_h_25(double *state, double *unused, double *out_2325222996689449646) {
  h_25(state, unused, out_2325222996689449646);
}
void car_H_25(double *state, double *unused, double *out_3271772249499668793) {
  H_25(state, unused, out_3271772249499668793);
}
void car_h_24(double *state, double *unused, double *out_6848076894841716204) {
  h_24(state, unused, out_6848076894841716204);
}
void car_H_24(double *state, double *unused, double *out_3303799557091849308) {
  H_24(state, unused, out_3303799557091849308);
}
void car_h_30(double *state, double *unused, double *out_8228581582135578611) {
  h_30(state, unused, out_8228581582135578611);
}
void car_H_30(double *state, double *unused, double *out_3644918091991947962) {
  H_30(state, unused, out_3644918091991947962);
}
void car_h_26(double *state, double *unused, double *out_7405610388304119622) {
  h_26(state, unused, out_7405610388304119622);
}
void car_H_26(double *state, double *unused, double *out_7013275568373725017) {
  H_26(state, unused, out_7013275568373725017);
}
void car_h_27(double *state, double *unused, double *out_2676450270971395999) {
  h_27(state, unused, out_2676450270971395999);
}
void car_H_27(double *state, double *unused, double *out_5575874508443333774) {
  H_27(state, unused, out_5575874508443333774);
}
void car_h_29(double *state, double *unused, double *out_1421853027307975865) {
  h_29(state, unused, out_1421853027307975865);
}
void car_H_29(double *state, double *unused, double *out_7289237235312884807) {
  H_29(state, unused, out_7289237235312884807);
}
void car_h_28(double *state, double *unused, double *out_6305518901035444766) {
  h_28(state, unused, out_6305518901035444766);
}
void car_H_28(double *state, double *unused, double *out_5325606963747558556) {
  H_28(state, unused, out_5325606963747558556);
}
void car_h_31(double *state, double *unused, double *out_2600417058973955535) {
  h_31(state, unused, out_2600417058973955535);
}
void car_H_31(double *state, double *unused, double *out_3241126287622708365) {
  H_31(state, unused, out_3241126287622708365);
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
