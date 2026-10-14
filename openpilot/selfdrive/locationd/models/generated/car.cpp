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
void err_fun(double *nom_x, double *delta_x, double *out_8401062644651369313) {
   out_8401062644651369313[0] = delta_x[0] + nom_x[0];
   out_8401062644651369313[1] = delta_x[1] + nom_x[1];
   out_8401062644651369313[2] = delta_x[2] + nom_x[2];
   out_8401062644651369313[3] = delta_x[3] + nom_x[3];
   out_8401062644651369313[4] = delta_x[4] + nom_x[4];
   out_8401062644651369313[5] = delta_x[5] + nom_x[5];
   out_8401062644651369313[6] = delta_x[6] + nom_x[6];
   out_8401062644651369313[7] = delta_x[7] + nom_x[7];
   out_8401062644651369313[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_1597386426371446775) {
   out_1597386426371446775[0] = -nom_x[0] + true_x[0];
   out_1597386426371446775[1] = -nom_x[1] + true_x[1];
   out_1597386426371446775[2] = -nom_x[2] + true_x[2];
   out_1597386426371446775[3] = -nom_x[3] + true_x[3];
   out_1597386426371446775[4] = -nom_x[4] + true_x[4];
   out_1597386426371446775[5] = -nom_x[5] + true_x[5];
   out_1597386426371446775[6] = -nom_x[6] + true_x[6];
   out_1597386426371446775[7] = -nom_x[7] + true_x[7];
   out_1597386426371446775[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_6673047517466386074) {
   out_6673047517466386074[0] = 1.0;
   out_6673047517466386074[1] = 0.0;
   out_6673047517466386074[2] = 0.0;
   out_6673047517466386074[3] = 0.0;
   out_6673047517466386074[4] = 0.0;
   out_6673047517466386074[5] = 0.0;
   out_6673047517466386074[6] = 0.0;
   out_6673047517466386074[7] = 0.0;
   out_6673047517466386074[8] = 0.0;
   out_6673047517466386074[9] = 0.0;
   out_6673047517466386074[10] = 1.0;
   out_6673047517466386074[11] = 0.0;
   out_6673047517466386074[12] = 0.0;
   out_6673047517466386074[13] = 0.0;
   out_6673047517466386074[14] = 0.0;
   out_6673047517466386074[15] = 0.0;
   out_6673047517466386074[16] = 0.0;
   out_6673047517466386074[17] = 0.0;
   out_6673047517466386074[18] = 0.0;
   out_6673047517466386074[19] = 0.0;
   out_6673047517466386074[20] = 1.0;
   out_6673047517466386074[21] = 0.0;
   out_6673047517466386074[22] = 0.0;
   out_6673047517466386074[23] = 0.0;
   out_6673047517466386074[24] = 0.0;
   out_6673047517466386074[25] = 0.0;
   out_6673047517466386074[26] = 0.0;
   out_6673047517466386074[27] = 0.0;
   out_6673047517466386074[28] = 0.0;
   out_6673047517466386074[29] = 0.0;
   out_6673047517466386074[30] = 1.0;
   out_6673047517466386074[31] = 0.0;
   out_6673047517466386074[32] = 0.0;
   out_6673047517466386074[33] = 0.0;
   out_6673047517466386074[34] = 0.0;
   out_6673047517466386074[35] = 0.0;
   out_6673047517466386074[36] = 0.0;
   out_6673047517466386074[37] = 0.0;
   out_6673047517466386074[38] = 0.0;
   out_6673047517466386074[39] = 0.0;
   out_6673047517466386074[40] = 1.0;
   out_6673047517466386074[41] = 0.0;
   out_6673047517466386074[42] = 0.0;
   out_6673047517466386074[43] = 0.0;
   out_6673047517466386074[44] = 0.0;
   out_6673047517466386074[45] = 0.0;
   out_6673047517466386074[46] = 0.0;
   out_6673047517466386074[47] = 0.0;
   out_6673047517466386074[48] = 0.0;
   out_6673047517466386074[49] = 0.0;
   out_6673047517466386074[50] = 1.0;
   out_6673047517466386074[51] = 0.0;
   out_6673047517466386074[52] = 0.0;
   out_6673047517466386074[53] = 0.0;
   out_6673047517466386074[54] = 0.0;
   out_6673047517466386074[55] = 0.0;
   out_6673047517466386074[56] = 0.0;
   out_6673047517466386074[57] = 0.0;
   out_6673047517466386074[58] = 0.0;
   out_6673047517466386074[59] = 0.0;
   out_6673047517466386074[60] = 1.0;
   out_6673047517466386074[61] = 0.0;
   out_6673047517466386074[62] = 0.0;
   out_6673047517466386074[63] = 0.0;
   out_6673047517466386074[64] = 0.0;
   out_6673047517466386074[65] = 0.0;
   out_6673047517466386074[66] = 0.0;
   out_6673047517466386074[67] = 0.0;
   out_6673047517466386074[68] = 0.0;
   out_6673047517466386074[69] = 0.0;
   out_6673047517466386074[70] = 1.0;
   out_6673047517466386074[71] = 0.0;
   out_6673047517466386074[72] = 0.0;
   out_6673047517466386074[73] = 0.0;
   out_6673047517466386074[74] = 0.0;
   out_6673047517466386074[75] = 0.0;
   out_6673047517466386074[76] = 0.0;
   out_6673047517466386074[77] = 0.0;
   out_6673047517466386074[78] = 0.0;
   out_6673047517466386074[79] = 0.0;
   out_6673047517466386074[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_9084958235864333770) {
   out_9084958235864333770[0] = state[0];
   out_9084958235864333770[1] = state[1];
   out_9084958235864333770[2] = state[2];
   out_9084958235864333770[3] = state[3];
   out_9084958235864333770[4] = state[4];
   out_9084958235864333770[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_9084958235864333770[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_9084958235864333770[7] = state[7];
   out_9084958235864333770[8] = state[8];
}
void F_fun(double *state, double dt, double *out_7170567397506903651) {
   out_7170567397506903651[0] = 1;
   out_7170567397506903651[1] = 0;
   out_7170567397506903651[2] = 0;
   out_7170567397506903651[3] = 0;
   out_7170567397506903651[4] = 0;
   out_7170567397506903651[5] = 0;
   out_7170567397506903651[6] = 0;
   out_7170567397506903651[7] = 0;
   out_7170567397506903651[8] = 0;
   out_7170567397506903651[9] = 0;
   out_7170567397506903651[10] = 1;
   out_7170567397506903651[11] = 0;
   out_7170567397506903651[12] = 0;
   out_7170567397506903651[13] = 0;
   out_7170567397506903651[14] = 0;
   out_7170567397506903651[15] = 0;
   out_7170567397506903651[16] = 0;
   out_7170567397506903651[17] = 0;
   out_7170567397506903651[18] = 0;
   out_7170567397506903651[19] = 0;
   out_7170567397506903651[20] = 1;
   out_7170567397506903651[21] = 0;
   out_7170567397506903651[22] = 0;
   out_7170567397506903651[23] = 0;
   out_7170567397506903651[24] = 0;
   out_7170567397506903651[25] = 0;
   out_7170567397506903651[26] = 0;
   out_7170567397506903651[27] = 0;
   out_7170567397506903651[28] = 0;
   out_7170567397506903651[29] = 0;
   out_7170567397506903651[30] = 1;
   out_7170567397506903651[31] = 0;
   out_7170567397506903651[32] = 0;
   out_7170567397506903651[33] = 0;
   out_7170567397506903651[34] = 0;
   out_7170567397506903651[35] = 0;
   out_7170567397506903651[36] = 0;
   out_7170567397506903651[37] = 0;
   out_7170567397506903651[38] = 0;
   out_7170567397506903651[39] = 0;
   out_7170567397506903651[40] = 1;
   out_7170567397506903651[41] = 0;
   out_7170567397506903651[42] = 0;
   out_7170567397506903651[43] = 0;
   out_7170567397506903651[44] = 0;
   out_7170567397506903651[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_7170567397506903651[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_7170567397506903651[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_7170567397506903651[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_7170567397506903651[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_7170567397506903651[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_7170567397506903651[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_7170567397506903651[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_7170567397506903651[53] = -9.8100000000000005*dt;
   out_7170567397506903651[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_7170567397506903651[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_7170567397506903651[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_7170567397506903651[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_7170567397506903651[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_7170567397506903651[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_7170567397506903651[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_7170567397506903651[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_7170567397506903651[62] = 0;
   out_7170567397506903651[63] = 0;
   out_7170567397506903651[64] = 0;
   out_7170567397506903651[65] = 0;
   out_7170567397506903651[66] = 0;
   out_7170567397506903651[67] = 0;
   out_7170567397506903651[68] = 0;
   out_7170567397506903651[69] = 0;
   out_7170567397506903651[70] = 1;
   out_7170567397506903651[71] = 0;
   out_7170567397506903651[72] = 0;
   out_7170567397506903651[73] = 0;
   out_7170567397506903651[74] = 0;
   out_7170567397506903651[75] = 0;
   out_7170567397506903651[76] = 0;
   out_7170567397506903651[77] = 0;
   out_7170567397506903651[78] = 0;
   out_7170567397506903651[79] = 0;
   out_7170567397506903651[80] = 1;
}
void h_25(double *state, double *unused, double *out_2817491058203070073) {
   out_2817491058203070073[0] = state[6];
}
void H_25(double *state, double *unused, double *out_2580508330330928305) {
   out_2580508330330928305[0] = 0;
   out_2580508330330928305[1] = 0;
   out_2580508330330928305[2] = 0;
   out_2580508330330928305[3] = 0;
   out_2580508330330928305[4] = 0;
   out_2580508330330928305[5] = 0;
   out_2580508330330928305[6] = 1;
   out_2580508330330928305[7] = 0;
   out_2580508330330928305[8] = 0;
}
void h_24(double *state, double *unused, double *out_1256144265869621667) {
   out_1256144265869621667[0] = state[4];
   out_1256144265869621667[1] = state[5];
}
void H_24(double *state, double *unused, double *out_2239813174325059958) {
   out_2239813174325059958[0] = 0;
   out_2239813174325059958[1] = 0;
   out_2239813174325059958[2] = 0;
   out_2239813174325059958[3] = 0;
   out_2239813174325059958[4] = 1;
   out_2239813174325059958[5] = 0;
   out_2239813174325059958[6] = 0;
   out_2239813174325059958[7] = 0;
   out_2239813174325059958[8] = 0;
   out_2239813174325059958[9] = 0;
   out_2239813174325059958[10] = 0;
   out_2239813174325059958[11] = 0;
   out_2239813174325059958[12] = 0;
   out_2239813174325059958[13] = 0;
   out_2239813174325059958[14] = 1;
   out_2239813174325059958[15] = 0;
   out_2239813174325059958[16] = 0;
   out_2239813174325059958[17] = 0;
}
void h_30(double *state, double *unused, double *out_3770336868273225090) {
   out_3770336868273225090[0] = state[4];
}
void H_30(double *state, double *unused, double *out_2451169383187688235) {
   out_2451169383187688235[0] = 0;
   out_2451169383187688235[1] = 0;
   out_2451169383187688235[2] = 0;
   out_2451169383187688235[3] = 0;
   out_2451169383187688235[4] = 1;
   out_2451169383187688235[5] = 0;
   out_2451169383187688235[6] = 0;
   out_2451169383187688235[7] = 0;
   out_2451169383187688235[8] = 0;
}
void h_26(double *state, double *unused, double *out_5250206544167251352) {
   out_5250206544167251352[0] = state[7];
}
void H_26(double *state, double *unused, double *out_1160994988543127919) {
   out_1160994988543127919[0] = 0;
   out_1160994988543127919[1] = 0;
   out_1160994988543127919[2] = 0;
   out_1160994988543127919[3] = 0;
   out_1160994988543127919[4] = 0;
   out_1160994988543127919[5] = 0;
   out_1160994988543127919[6] = 0;
   out_1160994988543127919[7] = 1;
   out_1160994988543127919[8] = 0;
}
void h_27(double *state, double *unused, double *out_4831854115108264269) {
   out_4831854115108264269[0] = state[3];
}
void H_27(double *state, double *unused, double *out_276406071387263324) {
   out_276406071387263324[0] = 0;
   out_276406071387263324[1] = 0;
   out_276406071387263324[2] = 0;
   out_276406071387263324[3] = 1;
   out_276406071387263324[4] = 0;
   out_276406071387263324[5] = 0;
   out_276406071387263324[6] = 0;
   out_276406071387263324[7] = 0;
   out_276406071387263324[8] = 0;
}
void h_29(double *state, double *unused, double *out_733550816828892405) {
   out_733550816828892405[0] = state[1];
}
void H_29(double *state, double *unused, double *out_2961400727502080419) {
   out_2961400727502080419[0] = 0;
   out_2961400727502080419[1] = 1;
   out_2961400727502080419[2] = 0;
   out_2961400727502080419[3] = 0;
   out_2961400727502080419[4] = 0;
   out_2961400727502080419[5] = 0;
   out_2961400727502080419[6] = 0;
   out_2961400727502080419[7] = 0;
   out_2961400727502080419[8] = 0;
}
void h_28(double *state, double *unused, double *out_4150115056898576496) {
   out_4150115056898576496[0] = state[0];
}
void H_28(double *state, double *unused, double *out_4925030999067406670) {
   out_4925030999067406670[0] = 1;
   out_4925030999067406670[1] = 0;
   out_4925030999067406670[2] = 0;
   out_4925030999067406670[3] = 0;
   out_4925030999067406670[4] = 0;
   out_4925030999067406670[5] = 0;
   out_4925030999067406670[6] = 0;
   out_4925030999067406670[7] = 0;
   out_4925030999067406670[8] = 0;
}
void h_31(double *state, double *unused, double *out_6454940586457092423) {
   out_6454940586457092423[0] = state[8];
}
void H_31(double *state, double *unused, double *out_2611154292207888733) {
   out_2611154292207888733[0] = 0;
   out_2611154292207888733[1] = 0;
   out_2611154292207888733[2] = 0;
   out_2611154292207888733[3] = 0;
   out_2611154292207888733[4] = 0;
   out_2611154292207888733[5] = 0;
   out_2611154292207888733[6] = 0;
   out_2611154292207888733[7] = 0;
   out_2611154292207888733[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_8401062644651369313) {
  err_fun(nom_x, delta_x, out_8401062644651369313);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_1597386426371446775) {
  inv_err_fun(nom_x, true_x, out_1597386426371446775);
}
void car_H_mod_fun(double *state, double *out_6673047517466386074) {
  H_mod_fun(state, out_6673047517466386074);
}
void car_f_fun(double *state, double dt, double *out_9084958235864333770) {
  f_fun(state,  dt, out_9084958235864333770);
}
void car_F_fun(double *state, double dt, double *out_7170567397506903651) {
  F_fun(state,  dt, out_7170567397506903651);
}
void car_h_25(double *state, double *unused, double *out_2817491058203070073) {
  h_25(state, unused, out_2817491058203070073);
}
void car_H_25(double *state, double *unused, double *out_2580508330330928305) {
  H_25(state, unused, out_2580508330330928305);
}
void car_h_24(double *state, double *unused, double *out_1256144265869621667) {
  h_24(state, unused, out_1256144265869621667);
}
void car_H_24(double *state, double *unused, double *out_2239813174325059958) {
  H_24(state, unused, out_2239813174325059958);
}
void car_h_30(double *state, double *unused, double *out_3770336868273225090) {
  h_30(state, unused, out_3770336868273225090);
}
void car_H_30(double *state, double *unused, double *out_2451169383187688235) {
  H_30(state, unused, out_2451169383187688235);
}
void car_h_26(double *state, double *unused, double *out_5250206544167251352) {
  h_26(state, unused, out_5250206544167251352);
}
void car_H_26(double *state, double *unused, double *out_1160994988543127919) {
  H_26(state, unused, out_1160994988543127919);
}
void car_h_27(double *state, double *unused, double *out_4831854115108264269) {
  h_27(state, unused, out_4831854115108264269);
}
void car_H_27(double *state, double *unused, double *out_276406071387263324) {
  H_27(state, unused, out_276406071387263324);
}
void car_h_29(double *state, double *unused, double *out_733550816828892405) {
  h_29(state, unused, out_733550816828892405);
}
void car_H_29(double *state, double *unused, double *out_2961400727502080419) {
  H_29(state, unused, out_2961400727502080419);
}
void car_h_28(double *state, double *unused, double *out_4150115056898576496) {
  h_28(state, unused, out_4150115056898576496);
}
void car_H_28(double *state, double *unused, double *out_4925030999067406670) {
  H_28(state, unused, out_4925030999067406670);
}
void car_h_31(double *state, double *unused, double *out_6454940586457092423) {
  h_31(state, unused, out_6454940586457092423);
}
void car_H_31(double *state, double *unused, double *out_2611154292207888733) {
  H_31(state, unused, out_2611154292207888733);
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
