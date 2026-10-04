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
void err_fun(double *nom_x, double *delta_x, double *out_8303558303892577205) {
   out_8303558303892577205[0] = delta_x[0] + nom_x[0];
   out_8303558303892577205[1] = delta_x[1] + nom_x[1];
   out_8303558303892577205[2] = delta_x[2] + nom_x[2];
   out_8303558303892577205[3] = delta_x[3] + nom_x[3];
   out_8303558303892577205[4] = delta_x[4] + nom_x[4];
   out_8303558303892577205[5] = delta_x[5] + nom_x[5];
   out_8303558303892577205[6] = delta_x[6] + nom_x[6];
   out_8303558303892577205[7] = delta_x[7] + nom_x[7];
   out_8303558303892577205[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_1062916904929925329) {
   out_1062916904929925329[0] = -nom_x[0] + true_x[0];
   out_1062916904929925329[1] = -nom_x[1] + true_x[1];
   out_1062916904929925329[2] = -nom_x[2] + true_x[2];
   out_1062916904929925329[3] = -nom_x[3] + true_x[3];
   out_1062916904929925329[4] = -nom_x[4] + true_x[4];
   out_1062916904929925329[5] = -nom_x[5] + true_x[5];
   out_1062916904929925329[6] = -nom_x[6] + true_x[6];
   out_1062916904929925329[7] = -nom_x[7] + true_x[7];
   out_1062916904929925329[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_3641608302244706687) {
   out_3641608302244706687[0] = 1.0;
   out_3641608302244706687[1] = 0.0;
   out_3641608302244706687[2] = 0.0;
   out_3641608302244706687[3] = 0.0;
   out_3641608302244706687[4] = 0.0;
   out_3641608302244706687[5] = 0.0;
   out_3641608302244706687[6] = 0.0;
   out_3641608302244706687[7] = 0.0;
   out_3641608302244706687[8] = 0.0;
   out_3641608302244706687[9] = 0.0;
   out_3641608302244706687[10] = 1.0;
   out_3641608302244706687[11] = 0.0;
   out_3641608302244706687[12] = 0.0;
   out_3641608302244706687[13] = 0.0;
   out_3641608302244706687[14] = 0.0;
   out_3641608302244706687[15] = 0.0;
   out_3641608302244706687[16] = 0.0;
   out_3641608302244706687[17] = 0.0;
   out_3641608302244706687[18] = 0.0;
   out_3641608302244706687[19] = 0.0;
   out_3641608302244706687[20] = 1.0;
   out_3641608302244706687[21] = 0.0;
   out_3641608302244706687[22] = 0.0;
   out_3641608302244706687[23] = 0.0;
   out_3641608302244706687[24] = 0.0;
   out_3641608302244706687[25] = 0.0;
   out_3641608302244706687[26] = 0.0;
   out_3641608302244706687[27] = 0.0;
   out_3641608302244706687[28] = 0.0;
   out_3641608302244706687[29] = 0.0;
   out_3641608302244706687[30] = 1.0;
   out_3641608302244706687[31] = 0.0;
   out_3641608302244706687[32] = 0.0;
   out_3641608302244706687[33] = 0.0;
   out_3641608302244706687[34] = 0.0;
   out_3641608302244706687[35] = 0.0;
   out_3641608302244706687[36] = 0.0;
   out_3641608302244706687[37] = 0.0;
   out_3641608302244706687[38] = 0.0;
   out_3641608302244706687[39] = 0.0;
   out_3641608302244706687[40] = 1.0;
   out_3641608302244706687[41] = 0.0;
   out_3641608302244706687[42] = 0.0;
   out_3641608302244706687[43] = 0.0;
   out_3641608302244706687[44] = 0.0;
   out_3641608302244706687[45] = 0.0;
   out_3641608302244706687[46] = 0.0;
   out_3641608302244706687[47] = 0.0;
   out_3641608302244706687[48] = 0.0;
   out_3641608302244706687[49] = 0.0;
   out_3641608302244706687[50] = 1.0;
   out_3641608302244706687[51] = 0.0;
   out_3641608302244706687[52] = 0.0;
   out_3641608302244706687[53] = 0.0;
   out_3641608302244706687[54] = 0.0;
   out_3641608302244706687[55] = 0.0;
   out_3641608302244706687[56] = 0.0;
   out_3641608302244706687[57] = 0.0;
   out_3641608302244706687[58] = 0.0;
   out_3641608302244706687[59] = 0.0;
   out_3641608302244706687[60] = 1.0;
   out_3641608302244706687[61] = 0.0;
   out_3641608302244706687[62] = 0.0;
   out_3641608302244706687[63] = 0.0;
   out_3641608302244706687[64] = 0.0;
   out_3641608302244706687[65] = 0.0;
   out_3641608302244706687[66] = 0.0;
   out_3641608302244706687[67] = 0.0;
   out_3641608302244706687[68] = 0.0;
   out_3641608302244706687[69] = 0.0;
   out_3641608302244706687[70] = 1.0;
   out_3641608302244706687[71] = 0.0;
   out_3641608302244706687[72] = 0.0;
   out_3641608302244706687[73] = 0.0;
   out_3641608302244706687[74] = 0.0;
   out_3641608302244706687[75] = 0.0;
   out_3641608302244706687[76] = 0.0;
   out_3641608302244706687[77] = 0.0;
   out_3641608302244706687[78] = 0.0;
   out_3641608302244706687[79] = 0.0;
   out_3641608302244706687[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_8905281951230386628) {
   out_8905281951230386628[0] = state[0];
   out_8905281951230386628[1] = state[1];
   out_8905281951230386628[2] = state[2];
   out_8905281951230386628[3] = state[3];
   out_8905281951230386628[4] = state[4];
   out_8905281951230386628[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_8905281951230386628[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_8905281951230386628[7] = state[7];
   out_8905281951230386628[8] = state[8];
}
void F_fun(double *state, double dt, double *out_3707619108862692258) {
   out_3707619108862692258[0] = 1;
   out_3707619108862692258[1] = 0;
   out_3707619108862692258[2] = 0;
   out_3707619108862692258[3] = 0;
   out_3707619108862692258[4] = 0;
   out_3707619108862692258[5] = 0;
   out_3707619108862692258[6] = 0;
   out_3707619108862692258[7] = 0;
   out_3707619108862692258[8] = 0;
   out_3707619108862692258[9] = 0;
   out_3707619108862692258[10] = 1;
   out_3707619108862692258[11] = 0;
   out_3707619108862692258[12] = 0;
   out_3707619108862692258[13] = 0;
   out_3707619108862692258[14] = 0;
   out_3707619108862692258[15] = 0;
   out_3707619108862692258[16] = 0;
   out_3707619108862692258[17] = 0;
   out_3707619108862692258[18] = 0;
   out_3707619108862692258[19] = 0;
   out_3707619108862692258[20] = 1;
   out_3707619108862692258[21] = 0;
   out_3707619108862692258[22] = 0;
   out_3707619108862692258[23] = 0;
   out_3707619108862692258[24] = 0;
   out_3707619108862692258[25] = 0;
   out_3707619108862692258[26] = 0;
   out_3707619108862692258[27] = 0;
   out_3707619108862692258[28] = 0;
   out_3707619108862692258[29] = 0;
   out_3707619108862692258[30] = 1;
   out_3707619108862692258[31] = 0;
   out_3707619108862692258[32] = 0;
   out_3707619108862692258[33] = 0;
   out_3707619108862692258[34] = 0;
   out_3707619108862692258[35] = 0;
   out_3707619108862692258[36] = 0;
   out_3707619108862692258[37] = 0;
   out_3707619108862692258[38] = 0;
   out_3707619108862692258[39] = 0;
   out_3707619108862692258[40] = 1;
   out_3707619108862692258[41] = 0;
   out_3707619108862692258[42] = 0;
   out_3707619108862692258[43] = 0;
   out_3707619108862692258[44] = 0;
   out_3707619108862692258[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_3707619108862692258[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_3707619108862692258[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_3707619108862692258[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_3707619108862692258[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_3707619108862692258[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_3707619108862692258[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_3707619108862692258[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_3707619108862692258[53] = -9.8100000000000005*dt;
   out_3707619108862692258[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_3707619108862692258[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_3707619108862692258[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_3707619108862692258[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_3707619108862692258[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_3707619108862692258[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_3707619108862692258[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_3707619108862692258[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_3707619108862692258[62] = 0;
   out_3707619108862692258[63] = 0;
   out_3707619108862692258[64] = 0;
   out_3707619108862692258[65] = 0;
   out_3707619108862692258[66] = 0;
   out_3707619108862692258[67] = 0;
   out_3707619108862692258[68] = 0;
   out_3707619108862692258[69] = 0;
   out_3707619108862692258[70] = 1;
   out_3707619108862692258[71] = 0;
   out_3707619108862692258[72] = 0;
   out_3707619108862692258[73] = 0;
   out_3707619108862692258[74] = 0;
   out_3707619108862692258[75] = 0;
   out_3707619108862692258[76] = 0;
   out_3707619108862692258[77] = 0;
   out_3707619108862692258[78] = 0;
   out_3707619108862692258[79] = 0;
   out_3707619108862692258[80] = 1;
}
void h_25(double *state, double *unused, double *out_8179086173107337673) {
   out_8179086173107337673[0] = state[6];
}
void H_25(double *state, double *unused, double *out_4279729730729153118) {
   out_4279729730729153118[0] = 0;
   out_4279729730729153118[1] = 0;
   out_4279729730729153118[2] = 0;
   out_4279729730729153118[3] = 0;
   out_4279729730729153118[4] = 0;
   out_4279729730729153118[5] = 0;
   out_4279729730729153118[6] = 1;
   out_4279729730729153118[7] = 0;
   out_4279729730729153118[8] = 0;
}
void h_24(double *state, double *unused, double *out_7632868272580967156) {
   out_7632868272580967156[0] = state[4];
   out_7632868272580967156[1] = state[5];
}
void H_24(double *state, double *unused, double *out_2107080131723653552) {
   out_2107080131723653552[0] = 0;
   out_2107080131723653552[1] = 0;
   out_2107080131723653552[2] = 0;
   out_2107080131723653552[3] = 0;
   out_2107080131723653552[4] = 1;
   out_2107080131723653552[5] = 0;
   out_2107080131723653552[6] = 0;
   out_2107080131723653552[7] = 0;
   out_2107080131723653552[8] = 0;
   out_2107080131723653552[9] = 0;
   out_2107080131723653552[10] = 0;
   out_2107080131723653552[11] = 0;
   out_2107080131723653552[12] = 0;
   out_2107080131723653552[13] = 0;
   out_2107080131723653552[14] = 1;
   out_2107080131723653552[15] = 0;
   out_2107080131723653552[16] = 0;
   out_2107080131723653552[17] = 0;
}
void h_30(double *state, double *unused, double *out_7903892110822831784) {
   out_7903892110822831784[0] = state[4];
}
void H_30(double *state, double *unused, double *out_6798062689236401745) {
   out_6798062689236401745[0] = 0;
   out_6798062689236401745[1] = 0;
   out_6798062689236401745[2] = 0;
   out_6798062689236401745[3] = 0;
   out_6798062689236401745[4] = 1;
   out_6798062689236401745[5] = 0;
   out_6798062689236401745[6] = 0;
   out_6798062689236401745[7] = 0;
   out_6798062689236401745[8] = 0;
}
void h_26(double *state, double *unused, double *out_901129407029766005) {
   out_901129407029766005[0] = state[7];
}
void H_26(double *state, double *unused, double *out_538226411855096894) {
   out_538226411855096894[0] = 0;
   out_538226411855096894[1] = 0;
   out_538226411855096894[2] = 0;
   out_538226411855096894[3] = 0;
   out_538226411855096894[4] = 0;
   out_538226411855096894[5] = 0;
   out_538226411855096894[6] = 0;
   out_538226411855096894[7] = 1;
   out_538226411855096894[8] = 0;
}
void h_27(double *state, double *unused, double *out_2953178957272012726) {
   out_2953178957272012726[0] = state[3];
}
void H_27(double *state, double *unused, double *out_4623299377435976834) {
   out_4623299377435976834[0] = 0;
   out_4623299377435976834[1] = 0;
   out_4623299377435976834[2] = 0;
   out_4623299377435976834[3] = 1;
   out_4623299377435976834[4] = 0;
   out_4623299377435976834[5] = 0;
   out_4623299377435976834[6] = 0;
   out_4623299377435976834[7] = 0;
   out_4623299377435976834[8] = 0;
}
void h_29(double *state, double *unused, double *out_684270570982009624) {
   out_684270570982009624[0] = state[1];
}
void H_29(double *state, double *unused, double *out_7308294033550793929) {
   out_7308294033550793929[0] = 0;
   out_7308294033550793929[1] = 1;
   out_7308294033550793929[2] = 0;
   out_7308294033550793929[3] = 0;
   out_7308294033550793929[4] = 0;
   out_7308294033550793929[5] = 0;
   out_7308294033550793929[6] = 0;
   out_7308294033550793929[7] = 0;
   out_7308294033550793929[8] = 0;
}
void h_28(double *state, double *unused, double *out_4120922758348154463) {
   out_4120922758348154463[0] = state[0];
}
void H_28(double *state, double *unused, double *out_2225895016481263355) {
   out_2225895016481263355[0] = 1;
   out_2225895016481263355[1] = 0;
   out_2225895016481263355[2] = 0;
   out_2225895016481263355[3] = 0;
   out_2225895016481263355[4] = 0;
   out_2225895016481263355[5] = 0;
   out_2225895016481263355[6] = 0;
   out_2225895016481263355[7] = 0;
   out_2225895016481263355[8] = 0;
}
void h_31(double *state, double *unused, double *out_6630208372348191593) {
   out_6630208372348191593[0] = state[8];
}
void H_31(double *state, double *unused, double *out_87981690378254582) {
   out_87981690378254582[0] = 0;
   out_87981690378254582[1] = 0;
   out_87981690378254582[2] = 0;
   out_87981690378254582[3] = 0;
   out_87981690378254582[4] = 0;
   out_87981690378254582[5] = 0;
   out_87981690378254582[6] = 0;
   out_87981690378254582[7] = 0;
   out_87981690378254582[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_8303558303892577205) {
  err_fun(nom_x, delta_x, out_8303558303892577205);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_1062916904929925329) {
  inv_err_fun(nom_x, true_x, out_1062916904929925329);
}
void car_H_mod_fun(double *state, double *out_3641608302244706687) {
  H_mod_fun(state, out_3641608302244706687);
}
void car_f_fun(double *state, double dt, double *out_8905281951230386628) {
  f_fun(state,  dt, out_8905281951230386628);
}
void car_F_fun(double *state, double dt, double *out_3707619108862692258) {
  F_fun(state,  dt, out_3707619108862692258);
}
void car_h_25(double *state, double *unused, double *out_8179086173107337673) {
  h_25(state, unused, out_8179086173107337673);
}
void car_H_25(double *state, double *unused, double *out_4279729730729153118) {
  H_25(state, unused, out_4279729730729153118);
}
void car_h_24(double *state, double *unused, double *out_7632868272580967156) {
  h_24(state, unused, out_7632868272580967156);
}
void car_H_24(double *state, double *unused, double *out_2107080131723653552) {
  H_24(state, unused, out_2107080131723653552);
}
void car_h_30(double *state, double *unused, double *out_7903892110822831784) {
  h_30(state, unused, out_7903892110822831784);
}
void car_H_30(double *state, double *unused, double *out_6798062689236401745) {
  H_30(state, unused, out_6798062689236401745);
}
void car_h_26(double *state, double *unused, double *out_901129407029766005) {
  h_26(state, unused, out_901129407029766005);
}
void car_H_26(double *state, double *unused, double *out_538226411855096894) {
  H_26(state, unused, out_538226411855096894);
}
void car_h_27(double *state, double *unused, double *out_2953178957272012726) {
  h_27(state, unused, out_2953178957272012726);
}
void car_H_27(double *state, double *unused, double *out_4623299377435976834) {
  H_27(state, unused, out_4623299377435976834);
}
void car_h_29(double *state, double *unused, double *out_684270570982009624) {
  h_29(state, unused, out_684270570982009624);
}
void car_H_29(double *state, double *unused, double *out_7308294033550793929) {
  H_29(state, unused, out_7308294033550793929);
}
void car_h_28(double *state, double *unused, double *out_4120922758348154463) {
  h_28(state, unused, out_4120922758348154463);
}
void car_H_28(double *state, double *unused, double *out_2225895016481263355) {
  H_28(state, unused, out_2225895016481263355);
}
void car_h_31(double *state, double *unused, double *out_6630208372348191593) {
  h_31(state, unused, out_6630208372348191593);
}
void car_H_31(double *state, double *unused, double *out_87981690378254582) {
  H_31(state, unused, out_87981690378254582);
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
