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
void err_fun(double *nom_x, double *delta_x, double *out_4635167675190451527) {
   out_4635167675190451527[0] = delta_x[0] + nom_x[0];
   out_4635167675190451527[1] = delta_x[1] + nom_x[1];
   out_4635167675190451527[2] = delta_x[2] + nom_x[2];
   out_4635167675190451527[3] = delta_x[3] + nom_x[3];
   out_4635167675190451527[4] = delta_x[4] + nom_x[4];
   out_4635167675190451527[5] = delta_x[5] + nom_x[5];
   out_4635167675190451527[6] = delta_x[6] + nom_x[6];
   out_4635167675190451527[7] = delta_x[7] + nom_x[7];
   out_4635167675190451527[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_3517853178278344902) {
   out_3517853178278344902[0] = -nom_x[0] + true_x[0];
   out_3517853178278344902[1] = -nom_x[1] + true_x[1];
   out_3517853178278344902[2] = -nom_x[2] + true_x[2];
   out_3517853178278344902[3] = -nom_x[3] + true_x[3];
   out_3517853178278344902[4] = -nom_x[4] + true_x[4];
   out_3517853178278344902[5] = -nom_x[5] + true_x[5];
   out_3517853178278344902[6] = -nom_x[6] + true_x[6];
   out_3517853178278344902[7] = -nom_x[7] + true_x[7];
   out_3517853178278344902[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_602949557029320551) {
   out_602949557029320551[0] = 1.0;
   out_602949557029320551[1] = 0.0;
   out_602949557029320551[2] = 0.0;
   out_602949557029320551[3] = 0.0;
   out_602949557029320551[4] = 0.0;
   out_602949557029320551[5] = 0.0;
   out_602949557029320551[6] = 0.0;
   out_602949557029320551[7] = 0.0;
   out_602949557029320551[8] = 0.0;
   out_602949557029320551[9] = 0.0;
   out_602949557029320551[10] = 1.0;
   out_602949557029320551[11] = 0.0;
   out_602949557029320551[12] = 0.0;
   out_602949557029320551[13] = 0.0;
   out_602949557029320551[14] = 0.0;
   out_602949557029320551[15] = 0.0;
   out_602949557029320551[16] = 0.0;
   out_602949557029320551[17] = 0.0;
   out_602949557029320551[18] = 0.0;
   out_602949557029320551[19] = 0.0;
   out_602949557029320551[20] = 1.0;
   out_602949557029320551[21] = 0.0;
   out_602949557029320551[22] = 0.0;
   out_602949557029320551[23] = 0.0;
   out_602949557029320551[24] = 0.0;
   out_602949557029320551[25] = 0.0;
   out_602949557029320551[26] = 0.0;
   out_602949557029320551[27] = 0.0;
   out_602949557029320551[28] = 0.0;
   out_602949557029320551[29] = 0.0;
   out_602949557029320551[30] = 1.0;
   out_602949557029320551[31] = 0.0;
   out_602949557029320551[32] = 0.0;
   out_602949557029320551[33] = 0.0;
   out_602949557029320551[34] = 0.0;
   out_602949557029320551[35] = 0.0;
   out_602949557029320551[36] = 0.0;
   out_602949557029320551[37] = 0.0;
   out_602949557029320551[38] = 0.0;
   out_602949557029320551[39] = 0.0;
   out_602949557029320551[40] = 1.0;
   out_602949557029320551[41] = 0.0;
   out_602949557029320551[42] = 0.0;
   out_602949557029320551[43] = 0.0;
   out_602949557029320551[44] = 0.0;
   out_602949557029320551[45] = 0.0;
   out_602949557029320551[46] = 0.0;
   out_602949557029320551[47] = 0.0;
   out_602949557029320551[48] = 0.0;
   out_602949557029320551[49] = 0.0;
   out_602949557029320551[50] = 1.0;
   out_602949557029320551[51] = 0.0;
   out_602949557029320551[52] = 0.0;
   out_602949557029320551[53] = 0.0;
   out_602949557029320551[54] = 0.0;
   out_602949557029320551[55] = 0.0;
   out_602949557029320551[56] = 0.0;
   out_602949557029320551[57] = 0.0;
   out_602949557029320551[58] = 0.0;
   out_602949557029320551[59] = 0.0;
   out_602949557029320551[60] = 1.0;
   out_602949557029320551[61] = 0.0;
   out_602949557029320551[62] = 0.0;
   out_602949557029320551[63] = 0.0;
   out_602949557029320551[64] = 0.0;
   out_602949557029320551[65] = 0.0;
   out_602949557029320551[66] = 0.0;
   out_602949557029320551[67] = 0.0;
   out_602949557029320551[68] = 0.0;
   out_602949557029320551[69] = 0.0;
   out_602949557029320551[70] = 1.0;
   out_602949557029320551[71] = 0.0;
   out_602949557029320551[72] = 0.0;
   out_602949557029320551[73] = 0.0;
   out_602949557029320551[74] = 0.0;
   out_602949557029320551[75] = 0.0;
   out_602949557029320551[76] = 0.0;
   out_602949557029320551[77] = 0.0;
   out_602949557029320551[78] = 0.0;
   out_602949557029320551[79] = 0.0;
   out_602949557029320551[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_113004381451582801) {
   out_113004381451582801[0] = state[0];
   out_113004381451582801[1] = state[1];
   out_113004381451582801[2] = state[2];
   out_113004381451582801[3] = state[3];
   out_113004381451582801[4] = state[4];
   out_113004381451582801[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_113004381451582801[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_113004381451582801[7] = state[7];
   out_113004381451582801[8] = state[8];
}
void F_fun(double *state, double dt, double *out_696983711093396292) {
   out_696983711093396292[0] = 1;
   out_696983711093396292[1] = 0;
   out_696983711093396292[2] = 0;
   out_696983711093396292[3] = 0;
   out_696983711093396292[4] = 0;
   out_696983711093396292[5] = 0;
   out_696983711093396292[6] = 0;
   out_696983711093396292[7] = 0;
   out_696983711093396292[8] = 0;
   out_696983711093396292[9] = 0;
   out_696983711093396292[10] = 1;
   out_696983711093396292[11] = 0;
   out_696983711093396292[12] = 0;
   out_696983711093396292[13] = 0;
   out_696983711093396292[14] = 0;
   out_696983711093396292[15] = 0;
   out_696983711093396292[16] = 0;
   out_696983711093396292[17] = 0;
   out_696983711093396292[18] = 0;
   out_696983711093396292[19] = 0;
   out_696983711093396292[20] = 1;
   out_696983711093396292[21] = 0;
   out_696983711093396292[22] = 0;
   out_696983711093396292[23] = 0;
   out_696983711093396292[24] = 0;
   out_696983711093396292[25] = 0;
   out_696983711093396292[26] = 0;
   out_696983711093396292[27] = 0;
   out_696983711093396292[28] = 0;
   out_696983711093396292[29] = 0;
   out_696983711093396292[30] = 1;
   out_696983711093396292[31] = 0;
   out_696983711093396292[32] = 0;
   out_696983711093396292[33] = 0;
   out_696983711093396292[34] = 0;
   out_696983711093396292[35] = 0;
   out_696983711093396292[36] = 0;
   out_696983711093396292[37] = 0;
   out_696983711093396292[38] = 0;
   out_696983711093396292[39] = 0;
   out_696983711093396292[40] = 1;
   out_696983711093396292[41] = 0;
   out_696983711093396292[42] = 0;
   out_696983711093396292[43] = 0;
   out_696983711093396292[44] = 0;
   out_696983711093396292[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_696983711093396292[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_696983711093396292[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_696983711093396292[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_696983711093396292[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_696983711093396292[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_696983711093396292[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_696983711093396292[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_696983711093396292[53] = -9.8100000000000005*dt;
   out_696983711093396292[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_696983711093396292[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_696983711093396292[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_696983711093396292[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_696983711093396292[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_696983711093396292[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_696983711093396292[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_696983711093396292[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_696983711093396292[62] = 0;
   out_696983711093396292[63] = 0;
   out_696983711093396292[64] = 0;
   out_696983711093396292[65] = 0;
   out_696983711093396292[66] = 0;
   out_696983711093396292[67] = 0;
   out_696983711093396292[68] = 0;
   out_696983711093396292[69] = 0;
   out_696983711093396292[70] = 1;
   out_696983711093396292[71] = 0;
   out_696983711093396292[72] = 0;
   out_696983711093396292[73] = 0;
   out_696983711093396292[74] = 0;
   out_696983711093396292[75] = 0;
   out_696983711093396292[76] = 0;
   out_696983711093396292[77] = 0;
   out_696983711093396292[78] = 0;
   out_696983711093396292[79] = 0;
   out_696983711093396292[80] = 1;
}
void h_25(double *state, double *unused, double *out_8706394861897294349) {
   out_8706394861897294349[0] = state[6];
}
void H_25(double *state, double *unused, double *out_4300742268155344289) {
   out_4300742268155344289[0] = 0;
   out_4300742268155344289[1] = 0;
   out_4300742268155344289[2] = 0;
   out_4300742268155344289[3] = 0;
   out_4300742268155344289[4] = 0;
   out_4300742268155344289[5] = 0;
   out_4300742268155344289[6] = 1;
   out_4300742268155344289[7] = 0;
   out_4300742268155344289[8] = 0;
}
void h_24(double *state, double *unused, double *out_2168250296672775669) {
   out_2168250296672775669[0] = state[4];
   out_2168250296672775669[1] = state[5];
}
void H_24(double *state, double *unused, double *out_4474150139656826605) {
   out_4474150139656826605[0] = 0;
   out_4474150139656826605[1] = 0;
   out_4474150139656826605[2] = 0;
   out_4474150139656826605[3] = 0;
   out_4474150139656826605[4] = 1;
   out_4474150139656826605[5] = 0;
   out_4474150139656826605[6] = 0;
   out_4474150139656826605[7] = 0;
   out_4474150139656826605[8] = 0;
   out_4474150139656826605[9] = 0;
   out_4474150139656826605[10] = 0;
   out_4474150139656826605[11] = 0;
   out_4474150139656826605[12] = 0;
   out_4474150139656826605[13] = 0;
   out_4474150139656826605[14] = 1;
   out_4474150139656826605[15] = 0;
   out_4474150139656826605[16] = 0;
   out_4474150139656826605[17] = 0;
}
void h_30(double *state, double *unused, double *out_3180337425346271236) {
   out_3180337425346271236[0] = state[4];
}
void H_30(double *state, double *unused, double *out_7229311464062590572) {
   out_7229311464062590572[0] = 0;
   out_7229311464062590572[1] = 0;
   out_7229311464062590572[2] = 0;
   out_7229311464062590572[3] = 0;
   out_7229311464062590572[4] = 1;
   out_7229311464062590572[5] = 0;
   out_7229311464062590572[6] = 0;
   out_7229311464062590572[7] = 0;
   out_7229311464062590572[8] = 0;
}
void h_26(double *state, double *unused, double *out_3755837170012439621) {
   out_3755837170012439621[0] = state[7];
}
void H_26(double *state, double *unused, double *out_559238949281288065) {
   out_559238949281288065[0] = 0;
   out_559238949281288065[1] = 0;
   out_559238949281288065[2] = 0;
   out_559238949281288065[3] = 0;
   out_559238949281288065[4] = 0;
   out_559238949281288065[5] = 0;
   out_559238949281288065[6] = 0;
   out_559238949281288065[7] = 1;
   out_559238949281288065[8] = 0;
}
void h_27(double *state, double *unused, double *out_7762885008995631914) {
   out_7762885008995631914[0] = state[3];
}
void H_27(double *state, double *unused, double *out_9042669297846536133) {
   out_9042669297846536133[0] = 0;
   out_9042669297846536133[1] = 0;
   out_9042669297846536133[2] = 0;
   out_9042669297846536133[3] = 1;
   out_9042669297846536133[4] = 0;
   out_9042669297846536133[5] = 0;
   out_9042669297846536133[6] = 0;
   out_9042669297846536133[7] = 0;
   out_9042669297846536133[8] = 0;
}
void h_29(double *state, double *unused, double *out_6312253616366748747) {
   out_6312253616366748747[0] = state[1];
}
void H_29(double *state, double *unused, double *out_7329306570976985100) {
   out_7329306570976985100[0] = 0;
   out_7329306570976985100[1] = 1;
   out_7329306570976985100[2] = 0;
   out_7329306570976985100[3] = 0;
   out_7329306570976985100[4] = 0;
   out_7329306570976985100[5] = 0;
   out_7329306570976985100[6] = 0;
   out_7329306570976985100[7] = 0;
   out_7329306570976985100[8] = 0;
}
void h_28(double *state, double *unused, double *out_2004900095001893958) {
   out_2004900095001893958[0] = state[0];
}
void H_28(double *state, double *unused, double *out_2246907553907454526) {
   out_2246907553907454526[0] = 1;
   out_2246907553907454526[1] = 0;
   out_2246907553907454526[2] = 0;
   out_2246907553907454526[3] = 0;
   out_2246907553907454526[4] = 0;
   out_2246907553907454526[5] = 0;
   out_2246907553907454526[6] = 0;
   out_2246907553907454526[7] = 0;
   out_2246907553907454526[8] = 0;
}
void h_31(double *state, double *unused, double *out_1100471735093715383) {
   out_1100471735093715383[0] = state[8];
}
void H_31(double *state, double *unused, double *out_4331388230032304717) {
   out_4331388230032304717[0] = 0;
   out_4331388230032304717[1] = 0;
   out_4331388230032304717[2] = 0;
   out_4331388230032304717[3] = 0;
   out_4331388230032304717[4] = 0;
   out_4331388230032304717[5] = 0;
   out_4331388230032304717[6] = 0;
   out_4331388230032304717[7] = 0;
   out_4331388230032304717[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_4635167675190451527) {
  err_fun(nom_x, delta_x, out_4635167675190451527);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_3517853178278344902) {
  inv_err_fun(nom_x, true_x, out_3517853178278344902);
}
void car_H_mod_fun(double *state, double *out_602949557029320551) {
  H_mod_fun(state, out_602949557029320551);
}
void car_f_fun(double *state, double dt, double *out_113004381451582801) {
  f_fun(state,  dt, out_113004381451582801);
}
void car_F_fun(double *state, double dt, double *out_696983711093396292) {
  F_fun(state,  dt, out_696983711093396292);
}
void car_h_25(double *state, double *unused, double *out_8706394861897294349) {
  h_25(state, unused, out_8706394861897294349);
}
void car_H_25(double *state, double *unused, double *out_4300742268155344289) {
  H_25(state, unused, out_4300742268155344289);
}
void car_h_24(double *state, double *unused, double *out_2168250296672775669) {
  h_24(state, unused, out_2168250296672775669);
}
void car_H_24(double *state, double *unused, double *out_4474150139656826605) {
  H_24(state, unused, out_4474150139656826605);
}
void car_h_30(double *state, double *unused, double *out_3180337425346271236) {
  h_30(state, unused, out_3180337425346271236);
}
void car_H_30(double *state, double *unused, double *out_7229311464062590572) {
  H_30(state, unused, out_7229311464062590572);
}
void car_h_26(double *state, double *unused, double *out_3755837170012439621) {
  h_26(state, unused, out_3755837170012439621);
}
void car_H_26(double *state, double *unused, double *out_559238949281288065) {
  H_26(state, unused, out_559238949281288065);
}
void car_h_27(double *state, double *unused, double *out_7762885008995631914) {
  h_27(state, unused, out_7762885008995631914);
}
void car_H_27(double *state, double *unused, double *out_9042669297846536133) {
  H_27(state, unused, out_9042669297846536133);
}
void car_h_29(double *state, double *unused, double *out_6312253616366748747) {
  h_29(state, unused, out_6312253616366748747);
}
void car_H_29(double *state, double *unused, double *out_7329306570976985100) {
  H_29(state, unused, out_7329306570976985100);
}
void car_h_28(double *state, double *unused, double *out_2004900095001893958) {
  h_28(state, unused, out_2004900095001893958);
}
void car_H_28(double *state, double *unused, double *out_2246907553907454526) {
  H_28(state, unused, out_2246907553907454526);
}
void car_h_31(double *state, double *unused, double *out_1100471735093715383) {
  h_31(state, unused, out_1100471735093715383);
}
void car_H_31(double *state, double *unused, double *out_4331388230032304717) {
  H_31(state, unused, out_4331388230032304717);
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
