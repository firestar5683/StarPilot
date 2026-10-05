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
void err_fun(double *nom_x, double *delta_x, double *out_7265162447446229961) {
   out_7265162447446229961[0] = delta_x[0] + nom_x[0];
   out_7265162447446229961[1] = delta_x[1] + nom_x[1];
   out_7265162447446229961[2] = delta_x[2] + nom_x[2];
   out_7265162447446229961[3] = delta_x[3] + nom_x[3];
   out_7265162447446229961[4] = delta_x[4] + nom_x[4];
   out_7265162447446229961[5] = delta_x[5] + nom_x[5];
   out_7265162447446229961[6] = delta_x[6] + nom_x[6];
   out_7265162447446229961[7] = delta_x[7] + nom_x[7];
   out_7265162447446229961[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_2534123790686773518) {
   out_2534123790686773518[0] = -nom_x[0] + true_x[0];
   out_2534123790686773518[1] = -nom_x[1] + true_x[1];
   out_2534123790686773518[2] = -nom_x[2] + true_x[2];
   out_2534123790686773518[3] = -nom_x[3] + true_x[3];
   out_2534123790686773518[4] = -nom_x[4] + true_x[4];
   out_2534123790686773518[5] = -nom_x[5] + true_x[5];
   out_2534123790686773518[6] = -nom_x[6] + true_x[6];
   out_2534123790686773518[7] = -nom_x[7] + true_x[7];
   out_2534123790686773518[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_1384469192892797747) {
   out_1384469192892797747[0] = 1.0;
   out_1384469192892797747[1] = 0.0;
   out_1384469192892797747[2] = 0.0;
   out_1384469192892797747[3] = 0.0;
   out_1384469192892797747[4] = 0.0;
   out_1384469192892797747[5] = 0.0;
   out_1384469192892797747[6] = 0.0;
   out_1384469192892797747[7] = 0.0;
   out_1384469192892797747[8] = 0.0;
   out_1384469192892797747[9] = 0.0;
   out_1384469192892797747[10] = 1.0;
   out_1384469192892797747[11] = 0.0;
   out_1384469192892797747[12] = 0.0;
   out_1384469192892797747[13] = 0.0;
   out_1384469192892797747[14] = 0.0;
   out_1384469192892797747[15] = 0.0;
   out_1384469192892797747[16] = 0.0;
   out_1384469192892797747[17] = 0.0;
   out_1384469192892797747[18] = 0.0;
   out_1384469192892797747[19] = 0.0;
   out_1384469192892797747[20] = 1.0;
   out_1384469192892797747[21] = 0.0;
   out_1384469192892797747[22] = 0.0;
   out_1384469192892797747[23] = 0.0;
   out_1384469192892797747[24] = 0.0;
   out_1384469192892797747[25] = 0.0;
   out_1384469192892797747[26] = 0.0;
   out_1384469192892797747[27] = 0.0;
   out_1384469192892797747[28] = 0.0;
   out_1384469192892797747[29] = 0.0;
   out_1384469192892797747[30] = 1.0;
   out_1384469192892797747[31] = 0.0;
   out_1384469192892797747[32] = 0.0;
   out_1384469192892797747[33] = 0.0;
   out_1384469192892797747[34] = 0.0;
   out_1384469192892797747[35] = 0.0;
   out_1384469192892797747[36] = 0.0;
   out_1384469192892797747[37] = 0.0;
   out_1384469192892797747[38] = 0.0;
   out_1384469192892797747[39] = 0.0;
   out_1384469192892797747[40] = 1.0;
   out_1384469192892797747[41] = 0.0;
   out_1384469192892797747[42] = 0.0;
   out_1384469192892797747[43] = 0.0;
   out_1384469192892797747[44] = 0.0;
   out_1384469192892797747[45] = 0.0;
   out_1384469192892797747[46] = 0.0;
   out_1384469192892797747[47] = 0.0;
   out_1384469192892797747[48] = 0.0;
   out_1384469192892797747[49] = 0.0;
   out_1384469192892797747[50] = 1.0;
   out_1384469192892797747[51] = 0.0;
   out_1384469192892797747[52] = 0.0;
   out_1384469192892797747[53] = 0.0;
   out_1384469192892797747[54] = 0.0;
   out_1384469192892797747[55] = 0.0;
   out_1384469192892797747[56] = 0.0;
   out_1384469192892797747[57] = 0.0;
   out_1384469192892797747[58] = 0.0;
   out_1384469192892797747[59] = 0.0;
   out_1384469192892797747[60] = 1.0;
   out_1384469192892797747[61] = 0.0;
   out_1384469192892797747[62] = 0.0;
   out_1384469192892797747[63] = 0.0;
   out_1384469192892797747[64] = 0.0;
   out_1384469192892797747[65] = 0.0;
   out_1384469192892797747[66] = 0.0;
   out_1384469192892797747[67] = 0.0;
   out_1384469192892797747[68] = 0.0;
   out_1384469192892797747[69] = 0.0;
   out_1384469192892797747[70] = 1.0;
   out_1384469192892797747[71] = 0.0;
   out_1384469192892797747[72] = 0.0;
   out_1384469192892797747[73] = 0.0;
   out_1384469192892797747[74] = 0.0;
   out_1384469192892797747[75] = 0.0;
   out_1384469192892797747[76] = 0.0;
   out_1384469192892797747[77] = 0.0;
   out_1384469192892797747[78] = 0.0;
   out_1384469192892797747[79] = 0.0;
   out_1384469192892797747[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_9101897029961662559) {
   out_9101897029961662559[0] = state[0];
   out_9101897029961662559[1] = state[1];
   out_9101897029961662559[2] = state[2];
   out_9101897029961662559[3] = state[3];
   out_9101897029961662559[4] = state[4];
   out_9101897029961662559[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_9101897029961662559[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_9101897029961662559[7] = state[7];
   out_9101897029961662559[8] = state[8];
}
void F_fun(double *state, double dt, double *out_680747621702192134) {
   out_680747621702192134[0] = 1;
   out_680747621702192134[1] = 0;
   out_680747621702192134[2] = 0;
   out_680747621702192134[3] = 0;
   out_680747621702192134[4] = 0;
   out_680747621702192134[5] = 0;
   out_680747621702192134[6] = 0;
   out_680747621702192134[7] = 0;
   out_680747621702192134[8] = 0;
   out_680747621702192134[9] = 0;
   out_680747621702192134[10] = 1;
   out_680747621702192134[11] = 0;
   out_680747621702192134[12] = 0;
   out_680747621702192134[13] = 0;
   out_680747621702192134[14] = 0;
   out_680747621702192134[15] = 0;
   out_680747621702192134[16] = 0;
   out_680747621702192134[17] = 0;
   out_680747621702192134[18] = 0;
   out_680747621702192134[19] = 0;
   out_680747621702192134[20] = 1;
   out_680747621702192134[21] = 0;
   out_680747621702192134[22] = 0;
   out_680747621702192134[23] = 0;
   out_680747621702192134[24] = 0;
   out_680747621702192134[25] = 0;
   out_680747621702192134[26] = 0;
   out_680747621702192134[27] = 0;
   out_680747621702192134[28] = 0;
   out_680747621702192134[29] = 0;
   out_680747621702192134[30] = 1;
   out_680747621702192134[31] = 0;
   out_680747621702192134[32] = 0;
   out_680747621702192134[33] = 0;
   out_680747621702192134[34] = 0;
   out_680747621702192134[35] = 0;
   out_680747621702192134[36] = 0;
   out_680747621702192134[37] = 0;
   out_680747621702192134[38] = 0;
   out_680747621702192134[39] = 0;
   out_680747621702192134[40] = 1;
   out_680747621702192134[41] = 0;
   out_680747621702192134[42] = 0;
   out_680747621702192134[43] = 0;
   out_680747621702192134[44] = 0;
   out_680747621702192134[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_680747621702192134[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_680747621702192134[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_680747621702192134[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_680747621702192134[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_680747621702192134[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_680747621702192134[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_680747621702192134[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_680747621702192134[53] = -9.8100000000000005*dt;
   out_680747621702192134[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_680747621702192134[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_680747621702192134[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_680747621702192134[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_680747621702192134[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_680747621702192134[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_680747621702192134[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_680747621702192134[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_680747621702192134[62] = 0;
   out_680747621702192134[63] = 0;
   out_680747621702192134[64] = 0;
   out_680747621702192134[65] = 0;
   out_680747621702192134[66] = 0;
   out_680747621702192134[67] = 0;
   out_680747621702192134[68] = 0;
   out_680747621702192134[69] = 0;
   out_680747621702192134[70] = 1;
   out_680747621702192134[71] = 0;
   out_680747621702192134[72] = 0;
   out_680747621702192134[73] = 0;
   out_680747621702192134[74] = 0;
   out_680747621702192134[75] = 0;
   out_680747621702192134[76] = 0;
   out_680747621702192134[77] = 0;
   out_680747621702192134[78] = 0;
   out_680747621702192134[79] = 0;
   out_680747621702192134[80] = 1;
}
void h_25(double *state, double *unused, double *out_952224570279587019) {
   out_952224570279587019[0] = state[6];
}
void H_25(double *state, double *unused, double *out_1889803635093094459) {
   out_1889803635093094459[0] = 0;
   out_1889803635093094459[1] = 0;
   out_1889803635093094459[2] = 0;
   out_1889803635093094459[3] = 0;
   out_1889803635093094459[4] = 0;
   out_1889803635093094459[5] = 0;
   out_1889803635093094459[6] = 1;
   out_1889803635093094459[7] = 0;
   out_1889803635093094459[8] = 0;
}
void h_24(double *state, double *unused, double *out_7823167244385071821) {
   out_7823167244385071821[0] = state[4];
   out_7823167244385071821[1] = state[5];
}
void H_24(double *state, double *unused, double *out_5891515713723603092) {
   out_5891515713723603092[0] = 0;
   out_5891515713723603092[1] = 0;
   out_5891515713723603092[2] = 0;
   out_5891515713723603092[3] = 0;
   out_5891515713723603092[4] = 1;
   out_5891515713723603092[5] = 0;
   out_5891515713723603092[6] = 0;
   out_5891515713723603092[7] = 0;
   out_5891515713723603092[8] = 0;
   out_5891515713723603092[9] = 0;
   out_5891515713723603092[10] = 0;
   out_5891515713723603092[11] = 0;
   out_5891515713723603092[12] = 0;
   out_5891515713723603092[13] = 0;
   out_5891515713723603092[14] = 1;
   out_5891515713723603092[15] = 0;
   out_5891515713723603092[16] = 0;
   out_5891515713723603092[17] = 0;
}
void h_30(double *state, double *unused, double *out_8854642026711422713) {
   out_8854642026711422713[0] = state[4];
}
void H_30(double *state, double *unused, double *out_8806493976584711214) {
   out_8806493976584711214[0] = 0;
   out_8806493976584711214[1] = 0;
   out_8806493976584711214[2] = 0;
   out_8806493976584711214[3] = 0;
   out_8806493976584711214[4] = 1;
   out_8806493976584711214[5] = 0;
   out_8806493976584711214[6] = 0;
   out_8806493976584711214[7] = 0;
   out_8806493976584711214[8] = 0;
}
void h_26(double *state, double *unused, double *out_8251326142034945196) {
   out_8251326142034945196[0] = state[7];
}
void H_26(double *state, double *unused, double *out_1851699683780961765) {
   out_1851699683780961765[0] = 0;
   out_1851699683780961765[1] = 0;
   out_1851699683780961765[2] = 0;
   out_1851699683780961765[3] = 0;
   out_1851699683780961765[4] = 0;
   out_1851699683780961765[5] = 0;
   out_1851699683780961765[6] = 0;
   out_1851699683780961765[7] = 1;
   out_1851699683780961765[8] = 0;
}
void h_27(double *state, double *unused, double *out_3989010621723919704) {
   out_3989010621723919704[0] = state[3];
}
void H_27(double *state, double *unused, double *out_6631730664784286303) {
   out_6631730664784286303[0] = 0;
   out_6631730664784286303[1] = 0;
   out_6631730664784286303[2] = 0;
   out_6631730664784286303[3] = 1;
   out_6631730664784286303[4] = 0;
   out_6631730664784286303[5] = 0;
   out_6631730664784286303[6] = 0;
   out_6631730664784286303[7] = 0;
   out_6631730664784286303[8] = 0;
}
void h_29(double *state, double *unused, double *out_7686898225635280976) {
   out_7686898225635280976[0] = state[1];
}
void H_29(double *state, double *unused, double *out_9130018752810448218) {
   out_9130018752810448218[0] = 0;
   out_9130018752810448218[1] = 1;
   out_9130018752810448218[2] = 0;
   out_9130018752810448218[3] = 0;
   out_9130018752810448218[4] = 0;
   out_9130018752810448218[5] = 0;
   out_9130018752810448218[6] = 0;
   out_9130018752810448218[7] = 0;
   out_9130018752810448218[8] = 0;
}
void h_28(double *state, double *unused, double *out_1236896594111405243) {
   out_1236896594111405243[0] = state[0];
}
void H_28(double *state, double *unused, double *out_4234326303829572824) {
   out_4234326303829572824[0] = 1;
   out_4234326303829572824[1] = 0;
   out_4234326303829572824[2] = 0;
   out_4234326303829572824[3] = 0;
   out_4234326303829572824[4] = 0;
   out_4234326303829572824[5] = 0;
   out_4234326303829572824[6] = 0;
   out_4234326303829572824[7] = 0;
   out_4234326303829572824[8] = 0;
}
void h_31(double *state, double *unused, double *out_1227418632564092908) {
   out_1227418632564092908[0] = state[8];
}
void H_31(double *state, double *unused, double *out_1920449596970054887) {
   out_1920449596970054887[0] = 0;
   out_1920449596970054887[1] = 0;
   out_1920449596970054887[2] = 0;
   out_1920449596970054887[3] = 0;
   out_1920449596970054887[4] = 0;
   out_1920449596970054887[5] = 0;
   out_1920449596970054887[6] = 0;
   out_1920449596970054887[7] = 0;
   out_1920449596970054887[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_7265162447446229961) {
  err_fun(nom_x, delta_x, out_7265162447446229961);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_2534123790686773518) {
  inv_err_fun(nom_x, true_x, out_2534123790686773518);
}
void car_H_mod_fun(double *state, double *out_1384469192892797747) {
  H_mod_fun(state, out_1384469192892797747);
}
void car_f_fun(double *state, double dt, double *out_9101897029961662559) {
  f_fun(state,  dt, out_9101897029961662559);
}
void car_F_fun(double *state, double dt, double *out_680747621702192134) {
  F_fun(state,  dt, out_680747621702192134);
}
void car_h_25(double *state, double *unused, double *out_952224570279587019) {
  h_25(state, unused, out_952224570279587019);
}
void car_H_25(double *state, double *unused, double *out_1889803635093094459) {
  H_25(state, unused, out_1889803635093094459);
}
void car_h_24(double *state, double *unused, double *out_7823167244385071821) {
  h_24(state, unused, out_7823167244385071821);
}
void car_H_24(double *state, double *unused, double *out_5891515713723603092) {
  H_24(state, unused, out_5891515713723603092);
}
void car_h_30(double *state, double *unused, double *out_8854642026711422713) {
  h_30(state, unused, out_8854642026711422713);
}
void car_H_30(double *state, double *unused, double *out_8806493976584711214) {
  H_30(state, unused, out_8806493976584711214);
}
void car_h_26(double *state, double *unused, double *out_8251326142034945196) {
  h_26(state, unused, out_8251326142034945196);
}
void car_H_26(double *state, double *unused, double *out_1851699683780961765) {
  H_26(state, unused, out_1851699683780961765);
}
void car_h_27(double *state, double *unused, double *out_3989010621723919704) {
  h_27(state, unused, out_3989010621723919704);
}
void car_H_27(double *state, double *unused, double *out_6631730664784286303) {
  H_27(state, unused, out_6631730664784286303);
}
void car_h_29(double *state, double *unused, double *out_7686898225635280976) {
  h_29(state, unused, out_7686898225635280976);
}
void car_H_29(double *state, double *unused, double *out_9130018752810448218) {
  H_29(state, unused, out_9130018752810448218);
}
void car_h_28(double *state, double *unused, double *out_1236896594111405243) {
  h_28(state, unused, out_1236896594111405243);
}
void car_H_28(double *state, double *unused, double *out_4234326303829572824) {
  H_28(state, unused, out_4234326303829572824);
}
void car_h_31(double *state, double *unused, double *out_1227418632564092908) {
  h_31(state, unused, out_1227418632564092908);
}
void car_H_31(double *state, double *unused, double *out_1920449596970054887) {
  H_31(state, unused, out_1920449596970054887);
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
