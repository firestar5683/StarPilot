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
void err_fun(double *nom_x, double *delta_x, double *out_9105893539066631470) {
   out_9105893539066631470[0] = delta_x[0] + nom_x[0];
   out_9105893539066631470[1] = delta_x[1] + nom_x[1];
   out_9105893539066631470[2] = delta_x[2] + nom_x[2];
   out_9105893539066631470[3] = delta_x[3] + nom_x[3];
   out_9105893539066631470[4] = delta_x[4] + nom_x[4];
   out_9105893539066631470[5] = delta_x[5] + nom_x[5];
   out_9105893539066631470[6] = delta_x[6] + nom_x[6];
   out_9105893539066631470[7] = delta_x[7] + nom_x[7];
   out_9105893539066631470[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_2201885575610208115) {
   out_2201885575610208115[0] = -nom_x[0] + true_x[0];
   out_2201885575610208115[1] = -nom_x[1] + true_x[1];
   out_2201885575610208115[2] = -nom_x[2] + true_x[2];
   out_2201885575610208115[3] = -nom_x[3] + true_x[3];
   out_2201885575610208115[4] = -nom_x[4] + true_x[4];
   out_2201885575610208115[5] = -nom_x[5] + true_x[5];
   out_2201885575610208115[6] = -nom_x[6] + true_x[6];
   out_2201885575610208115[7] = -nom_x[7] + true_x[7];
   out_2201885575610208115[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_8823093076762317206) {
   out_8823093076762317206[0] = 1.0;
   out_8823093076762317206[1] = 0.0;
   out_8823093076762317206[2] = 0.0;
   out_8823093076762317206[3] = 0.0;
   out_8823093076762317206[4] = 0.0;
   out_8823093076762317206[5] = 0.0;
   out_8823093076762317206[6] = 0.0;
   out_8823093076762317206[7] = 0.0;
   out_8823093076762317206[8] = 0.0;
   out_8823093076762317206[9] = 0.0;
   out_8823093076762317206[10] = 1.0;
   out_8823093076762317206[11] = 0.0;
   out_8823093076762317206[12] = 0.0;
   out_8823093076762317206[13] = 0.0;
   out_8823093076762317206[14] = 0.0;
   out_8823093076762317206[15] = 0.0;
   out_8823093076762317206[16] = 0.0;
   out_8823093076762317206[17] = 0.0;
   out_8823093076762317206[18] = 0.0;
   out_8823093076762317206[19] = 0.0;
   out_8823093076762317206[20] = 1.0;
   out_8823093076762317206[21] = 0.0;
   out_8823093076762317206[22] = 0.0;
   out_8823093076762317206[23] = 0.0;
   out_8823093076762317206[24] = 0.0;
   out_8823093076762317206[25] = 0.0;
   out_8823093076762317206[26] = 0.0;
   out_8823093076762317206[27] = 0.0;
   out_8823093076762317206[28] = 0.0;
   out_8823093076762317206[29] = 0.0;
   out_8823093076762317206[30] = 1.0;
   out_8823093076762317206[31] = 0.0;
   out_8823093076762317206[32] = 0.0;
   out_8823093076762317206[33] = 0.0;
   out_8823093076762317206[34] = 0.0;
   out_8823093076762317206[35] = 0.0;
   out_8823093076762317206[36] = 0.0;
   out_8823093076762317206[37] = 0.0;
   out_8823093076762317206[38] = 0.0;
   out_8823093076762317206[39] = 0.0;
   out_8823093076762317206[40] = 1.0;
   out_8823093076762317206[41] = 0.0;
   out_8823093076762317206[42] = 0.0;
   out_8823093076762317206[43] = 0.0;
   out_8823093076762317206[44] = 0.0;
   out_8823093076762317206[45] = 0.0;
   out_8823093076762317206[46] = 0.0;
   out_8823093076762317206[47] = 0.0;
   out_8823093076762317206[48] = 0.0;
   out_8823093076762317206[49] = 0.0;
   out_8823093076762317206[50] = 1.0;
   out_8823093076762317206[51] = 0.0;
   out_8823093076762317206[52] = 0.0;
   out_8823093076762317206[53] = 0.0;
   out_8823093076762317206[54] = 0.0;
   out_8823093076762317206[55] = 0.0;
   out_8823093076762317206[56] = 0.0;
   out_8823093076762317206[57] = 0.0;
   out_8823093076762317206[58] = 0.0;
   out_8823093076762317206[59] = 0.0;
   out_8823093076762317206[60] = 1.0;
   out_8823093076762317206[61] = 0.0;
   out_8823093076762317206[62] = 0.0;
   out_8823093076762317206[63] = 0.0;
   out_8823093076762317206[64] = 0.0;
   out_8823093076762317206[65] = 0.0;
   out_8823093076762317206[66] = 0.0;
   out_8823093076762317206[67] = 0.0;
   out_8823093076762317206[68] = 0.0;
   out_8823093076762317206[69] = 0.0;
   out_8823093076762317206[70] = 1.0;
   out_8823093076762317206[71] = 0.0;
   out_8823093076762317206[72] = 0.0;
   out_8823093076762317206[73] = 0.0;
   out_8823093076762317206[74] = 0.0;
   out_8823093076762317206[75] = 0.0;
   out_8823093076762317206[76] = 0.0;
   out_8823093076762317206[77] = 0.0;
   out_8823093076762317206[78] = 0.0;
   out_8823093076762317206[79] = 0.0;
   out_8823093076762317206[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_8757684582265239992) {
   out_8757684582265239992[0] = state[0];
   out_8757684582265239992[1] = state[1];
   out_8757684582265239992[2] = state[2];
   out_8757684582265239992[3] = state[3];
   out_8757684582265239992[4] = state[4];
   out_8757684582265239992[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_8757684582265239992[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_8757684582265239992[7] = state[7];
   out_8757684582265239992[8] = state[8];
}
void F_fun(double *state, double dt, double *out_2903520854157127208) {
   out_2903520854157127208[0] = 1;
   out_2903520854157127208[1] = 0;
   out_2903520854157127208[2] = 0;
   out_2903520854157127208[3] = 0;
   out_2903520854157127208[4] = 0;
   out_2903520854157127208[5] = 0;
   out_2903520854157127208[6] = 0;
   out_2903520854157127208[7] = 0;
   out_2903520854157127208[8] = 0;
   out_2903520854157127208[9] = 0;
   out_2903520854157127208[10] = 1;
   out_2903520854157127208[11] = 0;
   out_2903520854157127208[12] = 0;
   out_2903520854157127208[13] = 0;
   out_2903520854157127208[14] = 0;
   out_2903520854157127208[15] = 0;
   out_2903520854157127208[16] = 0;
   out_2903520854157127208[17] = 0;
   out_2903520854157127208[18] = 0;
   out_2903520854157127208[19] = 0;
   out_2903520854157127208[20] = 1;
   out_2903520854157127208[21] = 0;
   out_2903520854157127208[22] = 0;
   out_2903520854157127208[23] = 0;
   out_2903520854157127208[24] = 0;
   out_2903520854157127208[25] = 0;
   out_2903520854157127208[26] = 0;
   out_2903520854157127208[27] = 0;
   out_2903520854157127208[28] = 0;
   out_2903520854157127208[29] = 0;
   out_2903520854157127208[30] = 1;
   out_2903520854157127208[31] = 0;
   out_2903520854157127208[32] = 0;
   out_2903520854157127208[33] = 0;
   out_2903520854157127208[34] = 0;
   out_2903520854157127208[35] = 0;
   out_2903520854157127208[36] = 0;
   out_2903520854157127208[37] = 0;
   out_2903520854157127208[38] = 0;
   out_2903520854157127208[39] = 0;
   out_2903520854157127208[40] = 1;
   out_2903520854157127208[41] = 0;
   out_2903520854157127208[42] = 0;
   out_2903520854157127208[43] = 0;
   out_2903520854157127208[44] = 0;
   out_2903520854157127208[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_2903520854157127208[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_2903520854157127208[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_2903520854157127208[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_2903520854157127208[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_2903520854157127208[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_2903520854157127208[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_2903520854157127208[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_2903520854157127208[53] = -9.8100000000000005*dt;
   out_2903520854157127208[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_2903520854157127208[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_2903520854157127208[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_2903520854157127208[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_2903520854157127208[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_2903520854157127208[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_2903520854157127208[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_2903520854157127208[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_2903520854157127208[62] = 0;
   out_2903520854157127208[63] = 0;
   out_2903520854157127208[64] = 0;
   out_2903520854157127208[65] = 0;
   out_2903520854157127208[66] = 0;
   out_2903520854157127208[67] = 0;
   out_2903520854157127208[68] = 0;
   out_2903520854157127208[69] = 0;
   out_2903520854157127208[70] = 1;
   out_2903520854157127208[71] = 0;
   out_2903520854157127208[72] = 0;
   out_2903520854157127208[73] = 0;
   out_2903520854157127208[74] = 0;
   out_2903520854157127208[75] = 0;
   out_2903520854157127208[76] = 0;
   out_2903520854157127208[77] = 0;
   out_2903520854157127208[78] = 0;
   out_2903520854157127208[79] = 0;
   out_2903520854157127208[80] = 1;
}
void h_25(double *state, double *unused, double *out_6353487808218647336) {
   out_6353487808218647336[0] = state[6];
}
void H_25(double *state, double *unused, double *out_430462771034997173) {
   out_430462771034997173[0] = 0;
   out_430462771034997173[1] = 0;
   out_430462771034997173[2] = 0;
   out_430462771034997173[3] = 0;
   out_430462771034997173[4] = 0;
   out_430462771034997173[5] = 0;
   out_430462771034997173[6] = 1;
   out_430462771034997173[7] = 0;
   out_430462771034997173[8] = 0;
}
void h_24(double *state, double *unused, double *out_276973526775545327) {
   out_276973526775545327[0] = state[4];
   out_276973526775545327[1] = state[5];
}
void H_24(double *state, double *unused, double *out_1742186827970502393) {
   out_1742186827970502393[0] = 0;
   out_1742186827970502393[1] = 0;
   out_1742186827970502393[2] = 0;
   out_1742186827970502393[3] = 0;
   out_1742186827970502393[4] = 1;
   out_1742186827970502393[5] = 0;
   out_1742186827970502393[6] = 0;
   out_1742186827970502393[7] = 0;
   out_1742186827970502393[8] = 0;
   out_1742186827970502393[9] = 0;
   out_1742186827970502393[10] = 0;
   out_1742186827970502393[11] = 0;
   out_1742186827970502393[12] = 0;
   out_1742186827970502393[13] = 0;
   out_1742186827970502393[14] = 1;
   out_1742186827970502393[15] = 0;
   out_1742186827970502393[16] = 0;
   out_1742186827970502393[17] = 0;
}
void h_30(double *state, double *unused, double *out_2255184509939275472) {
   out_2255184509939275472[0] = state[4];
}
void H_30(double *state, double *unused, double *out_2948795729542245800) {
   out_2948795729542245800[0] = 0;
   out_2948795729542245800[1] = 0;
   out_2948795729542245800[2] = 0;
   out_2948795729542245800[3] = 0;
   out_2948795729542245800[4] = 1;
   out_2948795729542245800[5] = 0;
   out_2948795729542245800[6] = 0;
   out_2948795729542245800[7] = 0;
   out_2948795729542245800[8] = 0;
}
void h_26(double *state, double *unused, double *out_1273100416603977360) {
   out_1273100416603977360[0] = state[7];
}
void H_26(double *state, double *unused, double *out_3734988740795797774) {
   out_3734988740795797774[0] = 0;
   out_3734988740795797774[1] = 0;
   out_3734988740795797774[2] = 0;
   out_3734988740795797774[3] = 0;
   out_3734988740795797774[4] = 0;
   out_3734988740795797774[5] = 0;
   out_3734988740795797774[6] = 0;
   out_3734988740795797774[7] = 1;
   out_3734988740795797774[8] = 0;
}
void h_27(double *state, double *unused, double *out_2052169011425579317) {
   out_2052169011425579317[0] = state[3];
}
void H_27(double *state, double *unused, double *out_774032417741820889) {
   out_774032417741820889[0] = 0;
   out_774032417741820889[1] = 0;
   out_774032417741820889[2] = 0;
   out_774032417741820889[3] = 1;
   out_774032417741820889[4] = 0;
   out_774032417741820889[5] = 0;
   out_774032417741820889[6] = 0;
   out_774032417741820889[7] = 0;
   out_774032417741820889[8] = 0;
}
void h_29(double *state, double *unused, double *out_7256857777600121117) {
   out_7256857777600121117[0] = state[1];
}
void H_29(double *state, double *unused, double *out_3459027073856637984) {
   out_3459027073856637984[0] = 0;
   out_3459027073856637984[1] = 1;
   out_3459027073856637984[2] = 0;
   out_3459027073856637984[3] = 0;
   out_3459027073856637984[4] = 0;
   out_3459027073856637984[5] = 0;
   out_3459027073856637984[6] = 0;
   out_3459027073856637984[7] = 0;
   out_3459027073856637984[8] = 0;
}
void h_28(double *state, double *unused, double *out_2373191903872652216) {
   out_2373191903872652216[0] = state[0];
}
void H_28(double *state, double *unused, double *out_1623371943212892590) {
   out_1623371943212892590[0] = 1;
   out_1623371943212892590[1] = 0;
   out_1623371943212892590[2] = 0;
   out_1623371943212892590[3] = 0;
   out_1623371943212892590[4] = 0;
   out_1623371943212892590[5] = 0;
   out_1623371943212892590[6] = 0;
   out_1623371943212892590[7] = 0;
   out_1623371943212892590[8] = 0;
}
void h_31(double *state, double *unused, double *out_6078293745934141447) {
   out_6078293745934141447[0] = state[8];
}
void H_31(double *state, double *unused, double *out_3108780638562446298) {
   out_3108780638562446298[0] = 0;
   out_3108780638562446298[1] = 0;
   out_3108780638562446298[2] = 0;
   out_3108780638562446298[3] = 0;
   out_3108780638562446298[4] = 0;
   out_3108780638562446298[5] = 0;
   out_3108780638562446298[6] = 0;
   out_3108780638562446298[7] = 0;
   out_3108780638562446298[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_9105893539066631470) {
  err_fun(nom_x, delta_x, out_9105893539066631470);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_2201885575610208115) {
  inv_err_fun(nom_x, true_x, out_2201885575610208115);
}
void car_H_mod_fun(double *state, double *out_8823093076762317206) {
  H_mod_fun(state, out_8823093076762317206);
}
void car_f_fun(double *state, double dt, double *out_8757684582265239992) {
  f_fun(state,  dt, out_8757684582265239992);
}
void car_F_fun(double *state, double dt, double *out_2903520854157127208) {
  F_fun(state,  dt, out_2903520854157127208);
}
void car_h_25(double *state, double *unused, double *out_6353487808218647336) {
  h_25(state, unused, out_6353487808218647336);
}
void car_H_25(double *state, double *unused, double *out_430462771034997173) {
  H_25(state, unused, out_430462771034997173);
}
void car_h_24(double *state, double *unused, double *out_276973526775545327) {
  h_24(state, unused, out_276973526775545327);
}
void car_H_24(double *state, double *unused, double *out_1742186827970502393) {
  H_24(state, unused, out_1742186827970502393);
}
void car_h_30(double *state, double *unused, double *out_2255184509939275472) {
  h_30(state, unused, out_2255184509939275472);
}
void car_H_30(double *state, double *unused, double *out_2948795729542245800) {
  H_30(state, unused, out_2948795729542245800);
}
void car_h_26(double *state, double *unused, double *out_1273100416603977360) {
  h_26(state, unused, out_1273100416603977360);
}
void car_H_26(double *state, double *unused, double *out_3734988740795797774) {
  H_26(state, unused, out_3734988740795797774);
}
void car_h_27(double *state, double *unused, double *out_2052169011425579317) {
  h_27(state, unused, out_2052169011425579317);
}
void car_H_27(double *state, double *unused, double *out_774032417741820889) {
  H_27(state, unused, out_774032417741820889);
}
void car_h_29(double *state, double *unused, double *out_7256857777600121117) {
  h_29(state, unused, out_7256857777600121117);
}
void car_H_29(double *state, double *unused, double *out_3459027073856637984) {
  H_29(state, unused, out_3459027073856637984);
}
void car_h_28(double *state, double *unused, double *out_2373191903872652216) {
  h_28(state, unused, out_2373191903872652216);
}
void car_H_28(double *state, double *unused, double *out_1623371943212892590) {
  H_28(state, unused, out_1623371943212892590);
}
void car_h_31(double *state, double *unused, double *out_6078293745934141447) {
  h_31(state, unused, out_6078293745934141447);
}
void car_H_31(double *state, double *unused, double *out_3108780638562446298) {
  H_31(state, unused, out_3108780638562446298);
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
