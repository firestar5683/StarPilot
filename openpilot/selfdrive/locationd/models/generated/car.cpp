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
void err_fun(double *nom_x, double *delta_x, double *out_2647061973780188217) {
   out_2647061973780188217[0] = delta_x[0] + nom_x[0];
   out_2647061973780188217[1] = delta_x[1] + nom_x[1];
   out_2647061973780188217[2] = delta_x[2] + nom_x[2];
   out_2647061973780188217[3] = delta_x[3] + nom_x[3];
   out_2647061973780188217[4] = delta_x[4] + nom_x[4];
   out_2647061973780188217[5] = delta_x[5] + nom_x[5];
   out_2647061973780188217[6] = delta_x[6] + nom_x[6];
   out_2647061973780188217[7] = delta_x[7] + nom_x[7];
   out_2647061973780188217[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_2674623342919626392) {
   out_2674623342919626392[0] = -nom_x[0] + true_x[0];
   out_2674623342919626392[1] = -nom_x[1] + true_x[1];
   out_2674623342919626392[2] = -nom_x[2] + true_x[2];
   out_2674623342919626392[3] = -nom_x[3] + true_x[3];
   out_2674623342919626392[4] = -nom_x[4] + true_x[4];
   out_2674623342919626392[5] = -nom_x[5] + true_x[5];
   out_2674623342919626392[6] = -nom_x[6] + true_x[6];
   out_2674623342919626392[7] = -nom_x[7] + true_x[7];
   out_2674623342919626392[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_7441023162408258001) {
   out_7441023162408258001[0] = 1.0;
   out_7441023162408258001[1] = 0.0;
   out_7441023162408258001[2] = 0.0;
   out_7441023162408258001[3] = 0.0;
   out_7441023162408258001[4] = 0.0;
   out_7441023162408258001[5] = 0.0;
   out_7441023162408258001[6] = 0.0;
   out_7441023162408258001[7] = 0.0;
   out_7441023162408258001[8] = 0.0;
   out_7441023162408258001[9] = 0.0;
   out_7441023162408258001[10] = 1.0;
   out_7441023162408258001[11] = 0.0;
   out_7441023162408258001[12] = 0.0;
   out_7441023162408258001[13] = 0.0;
   out_7441023162408258001[14] = 0.0;
   out_7441023162408258001[15] = 0.0;
   out_7441023162408258001[16] = 0.0;
   out_7441023162408258001[17] = 0.0;
   out_7441023162408258001[18] = 0.0;
   out_7441023162408258001[19] = 0.0;
   out_7441023162408258001[20] = 1.0;
   out_7441023162408258001[21] = 0.0;
   out_7441023162408258001[22] = 0.0;
   out_7441023162408258001[23] = 0.0;
   out_7441023162408258001[24] = 0.0;
   out_7441023162408258001[25] = 0.0;
   out_7441023162408258001[26] = 0.0;
   out_7441023162408258001[27] = 0.0;
   out_7441023162408258001[28] = 0.0;
   out_7441023162408258001[29] = 0.0;
   out_7441023162408258001[30] = 1.0;
   out_7441023162408258001[31] = 0.0;
   out_7441023162408258001[32] = 0.0;
   out_7441023162408258001[33] = 0.0;
   out_7441023162408258001[34] = 0.0;
   out_7441023162408258001[35] = 0.0;
   out_7441023162408258001[36] = 0.0;
   out_7441023162408258001[37] = 0.0;
   out_7441023162408258001[38] = 0.0;
   out_7441023162408258001[39] = 0.0;
   out_7441023162408258001[40] = 1.0;
   out_7441023162408258001[41] = 0.0;
   out_7441023162408258001[42] = 0.0;
   out_7441023162408258001[43] = 0.0;
   out_7441023162408258001[44] = 0.0;
   out_7441023162408258001[45] = 0.0;
   out_7441023162408258001[46] = 0.0;
   out_7441023162408258001[47] = 0.0;
   out_7441023162408258001[48] = 0.0;
   out_7441023162408258001[49] = 0.0;
   out_7441023162408258001[50] = 1.0;
   out_7441023162408258001[51] = 0.0;
   out_7441023162408258001[52] = 0.0;
   out_7441023162408258001[53] = 0.0;
   out_7441023162408258001[54] = 0.0;
   out_7441023162408258001[55] = 0.0;
   out_7441023162408258001[56] = 0.0;
   out_7441023162408258001[57] = 0.0;
   out_7441023162408258001[58] = 0.0;
   out_7441023162408258001[59] = 0.0;
   out_7441023162408258001[60] = 1.0;
   out_7441023162408258001[61] = 0.0;
   out_7441023162408258001[62] = 0.0;
   out_7441023162408258001[63] = 0.0;
   out_7441023162408258001[64] = 0.0;
   out_7441023162408258001[65] = 0.0;
   out_7441023162408258001[66] = 0.0;
   out_7441023162408258001[67] = 0.0;
   out_7441023162408258001[68] = 0.0;
   out_7441023162408258001[69] = 0.0;
   out_7441023162408258001[70] = 1.0;
   out_7441023162408258001[71] = 0.0;
   out_7441023162408258001[72] = 0.0;
   out_7441023162408258001[73] = 0.0;
   out_7441023162408258001[74] = 0.0;
   out_7441023162408258001[75] = 0.0;
   out_7441023162408258001[76] = 0.0;
   out_7441023162408258001[77] = 0.0;
   out_7441023162408258001[78] = 0.0;
   out_7441023162408258001[79] = 0.0;
   out_7441023162408258001[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_7582243939014016185) {
   out_7582243939014016185[0] = state[0];
   out_7582243939014016185[1] = state[1];
   out_7582243939014016185[2] = state[2];
   out_7582243939014016185[3] = state[3];
   out_7582243939014016185[4] = state[4];
   out_7582243939014016185[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_7582243939014016185[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_7582243939014016185[7] = state[7];
   out_7582243939014016185[8] = state[8];
}
void F_fun(double *state, double dt, double *out_4968429326776778080) {
   out_4968429326776778080[0] = 1;
   out_4968429326776778080[1] = 0;
   out_4968429326776778080[2] = 0;
   out_4968429326776778080[3] = 0;
   out_4968429326776778080[4] = 0;
   out_4968429326776778080[5] = 0;
   out_4968429326776778080[6] = 0;
   out_4968429326776778080[7] = 0;
   out_4968429326776778080[8] = 0;
   out_4968429326776778080[9] = 0;
   out_4968429326776778080[10] = 1;
   out_4968429326776778080[11] = 0;
   out_4968429326776778080[12] = 0;
   out_4968429326776778080[13] = 0;
   out_4968429326776778080[14] = 0;
   out_4968429326776778080[15] = 0;
   out_4968429326776778080[16] = 0;
   out_4968429326776778080[17] = 0;
   out_4968429326776778080[18] = 0;
   out_4968429326776778080[19] = 0;
   out_4968429326776778080[20] = 1;
   out_4968429326776778080[21] = 0;
   out_4968429326776778080[22] = 0;
   out_4968429326776778080[23] = 0;
   out_4968429326776778080[24] = 0;
   out_4968429326776778080[25] = 0;
   out_4968429326776778080[26] = 0;
   out_4968429326776778080[27] = 0;
   out_4968429326776778080[28] = 0;
   out_4968429326776778080[29] = 0;
   out_4968429326776778080[30] = 1;
   out_4968429326776778080[31] = 0;
   out_4968429326776778080[32] = 0;
   out_4968429326776778080[33] = 0;
   out_4968429326776778080[34] = 0;
   out_4968429326776778080[35] = 0;
   out_4968429326776778080[36] = 0;
   out_4968429326776778080[37] = 0;
   out_4968429326776778080[38] = 0;
   out_4968429326776778080[39] = 0;
   out_4968429326776778080[40] = 1;
   out_4968429326776778080[41] = 0;
   out_4968429326776778080[42] = 0;
   out_4968429326776778080[43] = 0;
   out_4968429326776778080[44] = 0;
   out_4968429326776778080[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_4968429326776778080[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_4968429326776778080[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_4968429326776778080[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_4968429326776778080[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_4968429326776778080[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_4968429326776778080[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_4968429326776778080[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_4968429326776778080[53] = -9.8100000000000005*dt;
   out_4968429326776778080[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_4968429326776778080[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_4968429326776778080[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_4968429326776778080[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_4968429326776778080[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_4968429326776778080[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_4968429326776778080[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_4968429326776778080[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_4968429326776778080[62] = 0;
   out_4968429326776778080[63] = 0;
   out_4968429326776778080[64] = 0;
   out_4968429326776778080[65] = 0;
   out_4968429326776778080[66] = 0;
   out_4968429326776778080[67] = 0;
   out_4968429326776778080[68] = 0;
   out_4968429326776778080[69] = 0;
   out_4968429326776778080[70] = 1;
   out_4968429326776778080[71] = 0;
   out_4968429326776778080[72] = 0;
   out_4968429326776778080[73] = 0;
   out_4968429326776778080[74] = 0;
   out_4968429326776778080[75] = 0;
   out_4968429326776778080[76] = 0;
   out_4968429326776778080[77] = 0;
   out_4968429326776778080[78] = 0;
   out_4968429326776778080[79] = 0;
   out_4968429326776778080[80] = 1;
}
void h_25(double *state, double *unused, double *out_3424118357067698509) {
   out_3424118357067698509[0] = state[6];
}
void H_25(double *state, double *unused, double *out_4347004889615861493) {
   out_4347004889615861493[0] = 0;
   out_4347004889615861493[1] = 0;
   out_4347004889615861493[2] = 0;
   out_4347004889615861493[3] = 0;
   out_4347004889615861493[4] = 0;
   out_4347004889615861493[5] = 0;
   out_4347004889615861493[6] = 1;
   out_4347004889615861493[7] = 0;
   out_4347004889615861493[8] = 0;
}
void h_24(double *state, double *unused, double *out_1209077948684966761) {
   out_1209077948684966761[0] = state[4];
   out_1209077948684966761[1] = state[5];
}
void H_24(double *state, double *unused, double *out_2933976641577452656) {
   out_2933976641577452656[0] = 0;
   out_2933976641577452656[1] = 0;
   out_2933976641577452656[2] = 0;
   out_2933976641577452656[3] = 0;
   out_2933976641577452656[4] = 1;
   out_2933976641577452656[5] = 0;
   out_2933976641577452656[6] = 0;
   out_2933976641577452656[7] = 0;
   out_2933976641577452656[8] = 0;
   out_2933976641577452656[9] = 0;
   out_2933976641577452656[10] = 0;
   out_2933976641577452656[11] = 0;
   out_2933976641577452656[12] = 0;
   out_2933976641577452656[13] = 0;
   out_2933976641577452656[14] = 1;
   out_2933976641577452656[15] = 0;
   out_2933976641577452656[16] = 0;
   out_2933976641577452656[17] = 0;
}
void h_30(double *state, double *unused, double *out_4457154293686350676) {
   out_4457154293686350676[0] = state[4];
}
void H_30(double *state, double *unused, double *out_1828671931108612866) {
   out_1828671931108612866[0] = 0;
   out_1828671931108612866[1] = 0;
   out_1828671931108612866[2] = 0;
   out_1828671931108612866[3] = 0;
   out_1828671931108612866[4] = 1;
   out_1828671931108612866[5] = 0;
   out_1828671931108612866[6] = 0;
   out_1828671931108612866[7] = 0;
   out_1828671931108612866[8] = 0;
}
void h_26(double *state, double *unused, double *out_1458476460047511660) {
   out_1458476460047511660[0] = state[7];
}
void H_26(double *state, double *unused, double *out_8088508208489917717) {
   out_8088508208489917717[0] = 0;
   out_8088508208489917717[1] = 0;
   out_8088508208489917717[2] = 0;
   out_8088508208489917717[3] = 0;
   out_8088508208489917717[4] = 0;
   out_8088508208489917717[5] = 0;
   out_8088508208489917717[6] = 0;
   out_8088508208489917717[7] = 1;
   out_8088508208489917717[8] = 0;
}
void h_27(double *state, double *unused, double *out_4972164798077654358) {
   out_4972164798077654358[0] = state[3];
}
void H_27(double *state, double *unused, double *out_4003435242909037777) {
   out_4003435242909037777[0] = 0;
   out_4003435242909037777[1] = 0;
   out_4003435242909037777[2] = 0;
   out_4003435242909037777[3] = 1;
   out_4003435242909037777[4] = 0;
   out_4003435242909037777[5] = 0;
   out_4003435242909037777[6] = 0;
   out_4003435242909037777[7] = 0;
   out_4003435242909037777[8] = 0;
}
void h_29(double *state, double *unused, double *out_1798670428272696578) {
   out_1798670428272696578[0] = state[1];
}
void H_29(double *state, double *unused, double *out_1318440586794220682) {
   out_1318440586794220682[0] = 0;
   out_1318440586794220682[1] = 1;
   out_1318440586794220682[2] = 0;
   out_1318440586794220682[3] = 0;
   out_1318440586794220682[4] = 0;
   out_1318440586794220682[5] = 0;
   out_1318440586794220682[6] = 0;
   out_1318440586794220682[7] = 0;
   out_1318440586794220682[8] = 0;
}
void h_28(double *state, double *unused, double *out_7680074346326341526) {
   out_7680074346326341526[0] = state[0];
}
void H_28(double *state, double *unused, double *out_6400839603863751256) {
   out_6400839603863751256[0] = 1;
   out_6400839603863751256[1] = 0;
   out_6400839603863751256[2] = 0;
   out_6400839603863751256[3] = 0;
   out_6400839603863751256[4] = 0;
   out_6400839603863751256[5] = 0;
   out_6400839603863751256[6] = 0;
   out_6400839603863751256[7] = 0;
   out_6400839603863751256[8] = 0;
}
void h_31(double *state, double *unused, double *out_5215759119650843375) {
   out_5215759119650843375[0] = state[8];
}
void H_31(double *state, double *unused, double *out_8714716310723269193) {
   out_8714716310723269193[0] = 0;
   out_8714716310723269193[1] = 0;
   out_8714716310723269193[2] = 0;
   out_8714716310723269193[3] = 0;
   out_8714716310723269193[4] = 0;
   out_8714716310723269193[5] = 0;
   out_8714716310723269193[6] = 0;
   out_8714716310723269193[7] = 0;
   out_8714716310723269193[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_2647061973780188217) {
  err_fun(nom_x, delta_x, out_2647061973780188217);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_2674623342919626392) {
  inv_err_fun(nom_x, true_x, out_2674623342919626392);
}
void car_H_mod_fun(double *state, double *out_7441023162408258001) {
  H_mod_fun(state, out_7441023162408258001);
}
void car_f_fun(double *state, double dt, double *out_7582243939014016185) {
  f_fun(state,  dt, out_7582243939014016185);
}
void car_F_fun(double *state, double dt, double *out_4968429326776778080) {
  F_fun(state,  dt, out_4968429326776778080);
}
void car_h_25(double *state, double *unused, double *out_3424118357067698509) {
  h_25(state, unused, out_3424118357067698509);
}
void car_H_25(double *state, double *unused, double *out_4347004889615861493) {
  H_25(state, unused, out_4347004889615861493);
}
void car_h_24(double *state, double *unused, double *out_1209077948684966761) {
  h_24(state, unused, out_1209077948684966761);
}
void car_H_24(double *state, double *unused, double *out_2933976641577452656) {
  H_24(state, unused, out_2933976641577452656);
}
void car_h_30(double *state, double *unused, double *out_4457154293686350676) {
  h_30(state, unused, out_4457154293686350676);
}
void car_H_30(double *state, double *unused, double *out_1828671931108612866) {
  H_30(state, unused, out_1828671931108612866);
}
void car_h_26(double *state, double *unused, double *out_1458476460047511660) {
  h_26(state, unused, out_1458476460047511660);
}
void car_H_26(double *state, double *unused, double *out_8088508208489917717) {
  H_26(state, unused, out_8088508208489917717);
}
void car_h_27(double *state, double *unused, double *out_4972164798077654358) {
  h_27(state, unused, out_4972164798077654358);
}
void car_H_27(double *state, double *unused, double *out_4003435242909037777) {
  H_27(state, unused, out_4003435242909037777);
}
void car_h_29(double *state, double *unused, double *out_1798670428272696578) {
  h_29(state, unused, out_1798670428272696578);
}
void car_H_29(double *state, double *unused, double *out_1318440586794220682) {
  H_29(state, unused, out_1318440586794220682);
}
void car_h_28(double *state, double *unused, double *out_7680074346326341526) {
  h_28(state, unused, out_7680074346326341526);
}
void car_H_28(double *state, double *unused, double *out_6400839603863751256) {
  H_28(state, unused, out_6400839603863751256);
}
void car_h_31(double *state, double *unused, double *out_5215759119650843375) {
  h_31(state, unused, out_5215759119650843375);
}
void car_H_31(double *state, double *unused, double *out_8714716310723269193) {
  H_31(state, unused, out_8714716310723269193);
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
