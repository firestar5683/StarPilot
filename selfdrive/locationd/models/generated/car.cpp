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
void err_fun(double *nom_x, double *delta_x, double *out_395710906661730109) {
   out_395710906661730109[0] = delta_x[0] + nom_x[0];
   out_395710906661730109[1] = delta_x[1] + nom_x[1];
   out_395710906661730109[2] = delta_x[2] + nom_x[2];
   out_395710906661730109[3] = delta_x[3] + nom_x[3];
   out_395710906661730109[4] = delta_x[4] + nom_x[4];
   out_395710906661730109[5] = delta_x[5] + nom_x[5];
   out_395710906661730109[6] = delta_x[6] + nom_x[6];
   out_395710906661730109[7] = delta_x[7] + nom_x[7];
   out_395710906661730109[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_6370952191766860566) {
   out_6370952191766860566[0] = -nom_x[0] + true_x[0];
   out_6370952191766860566[1] = -nom_x[1] + true_x[1];
   out_6370952191766860566[2] = -nom_x[2] + true_x[2];
   out_6370952191766860566[3] = -nom_x[3] + true_x[3];
   out_6370952191766860566[4] = -nom_x[4] + true_x[4];
   out_6370952191766860566[5] = -nom_x[5] + true_x[5];
   out_6370952191766860566[6] = -nom_x[6] + true_x[6];
   out_6370952191766860566[7] = -nom_x[7] + true_x[7];
   out_6370952191766860566[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_8610422609060100183) {
   out_8610422609060100183[0] = 1.0;
   out_8610422609060100183[1] = 0.0;
   out_8610422609060100183[2] = 0.0;
   out_8610422609060100183[3] = 0.0;
   out_8610422609060100183[4] = 0.0;
   out_8610422609060100183[5] = 0.0;
   out_8610422609060100183[6] = 0.0;
   out_8610422609060100183[7] = 0.0;
   out_8610422609060100183[8] = 0.0;
   out_8610422609060100183[9] = 0.0;
   out_8610422609060100183[10] = 1.0;
   out_8610422609060100183[11] = 0.0;
   out_8610422609060100183[12] = 0.0;
   out_8610422609060100183[13] = 0.0;
   out_8610422609060100183[14] = 0.0;
   out_8610422609060100183[15] = 0.0;
   out_8610422609060100183[16] = 0.0;
   out_8610422609060100183[17] = 0.0;
   out_8610422609060100183[18] = 0.0;
   out_8610422609060100183[19] = 0.0;
   out_8610422609060100183[20] = 1.0;
   out_8610422609060100183[21] = 0.0;
   out_8610422609060100183[22] = 0.0;
   out_8610422609060100183[23] = 0.0;
   out_8610422609060100183[24] = 0.0;
   out_8610422609060100183[25] = 0.0;
   out_8610422609060100183[26] = 0.0;
   out_8610422609060100183[27] = 0.0;
   out_8610422609060100183[28] = 0.0;
   out_8610422609060100183[29] = 0.0;
   out_8610422609060100183[30] = 1.0;
   out_8610422609060100183[31] = 0.0;
   out_8610422609060100183[32] = 0.0;
   out_8610422609060100183[33] = 0.0;
   out_8610422609060100183[34] = 0.0;
   out_8610422609060100183[35] = 0.0;
   out_8610422609060100183[36] = 0.0;
   out_8610422609060100183[37] = 0.0;
   out_8610422609060100183[38] = 0.0;
   out_8610422609060100183[39] = 0.0;
   out_8610422609060100183[40] = 1.0;
   out_8610422609060100183[41] = 0.0;
   out_8610422609060100183[42] = 0.0;
   out_8610422609060100183[43] = 0.0;
   out_8610422609060100183[44] = 0.0;
   out_8610422609060100183[45] = 0.0;
   out_8610422609060100183[46] = 0.0;
   out_8610422609060100183[47] = 0.0;
   out_8610422609060100183[48] = 0.0;
   out_8610422609060100183[49] = 0.0;
   out_8610422609060100183[50] = 1.0;
   out_8610422609060100183[51] = 0.0;
   out_8610422609060100183[52] = 0.0;
   out_8610422609060100183[53] = 0.0;
   out_8610422609060100183[54] = 0.0;
   out_8610422609060100183[55] = 0.0;
   out_8610422609060100183[56] = 0.0;
   out_8610422609060100183[57] = 0.0;
   out_8610422609060100183[58] = 0.0;
   out_8610422609060100183[59] = 0.0;
   out_8610422609060100183[60] = 1.0;
   out_8610422609060100183[61] = 0.0;
   out_8610422609060100183[62] = 0.0;
   out_8610422609060100183[63] = 0.0;
   out_8610422609060100183[64] = 0.0;
   out_8610422609060100183[65] = 0.0;
   out_8610422609060100183[66] = 0.0;
   out_8610422609060100183[67] = 0.0;
   out_8610422609060100183[68] = 0.0;
   out_8610422609060100183[69] = 0.0;
   out_8610422609060100183[70] = 1.0;
   out_8610422609060100183[71] = 0.0;
   out_8610422609060100183[72] = 0.0;
   out_8610422609060100183[73] = 0.0;
   out_8610422609060100183[74] = 0.0;
   out_8610422609060100183[75] = 0.0;
   out_8610422609060100183[76] = 0.0;
   out_8610422609060100183[77] = 0.0;
   out_8610422609060100183[78] = 0.0;
   out_8610422609060100183[79] = 0.0;
   out_8610422609060100183[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_7209711513462721716) {
   out_7209711513462721716[0] = state[0];
   out_7209711513462721716[1] = state[1];
   out_7209711513462721716[2] = state[2];
   out_7209711513462721716[3] = state[3];
   out_7209711513462721716[4] = state[4];
   out_7209711513462721716[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_7209711513462721716[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_7209711513462721716[7] = state[7];
   out_7209711513462721716[8] = state[8];
}
void F_fun(double *state, double dt, double *out_832953036043329844) {
   out_832953036043329844[0] = 1;
   out_832953036043329844[1] = 0;
   out_832953036043329844[2] = 0;
   out_832953036043329844[3] = 0;
   out_832953036043329844[4] = 0;
   out_832953036043329844[5] = 0;
   out_832953036043329844[6] = 0;
   out_832953036043329844[7] = 0;
   out_832953036043329844[8] = 0;
   out_832953036043329844[9] = 0;
   out_832953036043329844[10] = 1;
   out_832953036043329844[11] = 0;
   out_832953036043329844[12] = 0;
   out_832953036043329844[13] = 0;
   out_832953036043329844[14] = 0;
   out_832953036043329844[15] = 0;
   out_832953036043329844[16] = 0;
   out_832953036043329844[17] = 0;
   out_832953036043329844[18] = 0;
   out_832953036043329844[19] = 0;
   out_832953036043329844[20] = 1;
   out_832953036043329844[21] = 0;
   out_832953036043329844[22] = 0;
   out_832953036043329844[23] = 0;
   out_832953036043329844[24] = 0;
   out_832953036043329844[25] = 0;
   out_832953036043329844[26] = 0;
   out_832953036043329844[27] = 0;
   out_832953036043329844[28] = 0;
   out_832953036043329844[29] = 0;
   out_832953036043329844[30] = 1;
   out_832953036043329844[31] = 0;
   out_832953036043329844[32] = 0;
   out_832953036043329844[33] = 0;
   out_832953036043329844[34] = 0;
   out_832953036043329844[35] = 0;
   out_832953036043329844[36] = 0;
   out_832953036043329844[37] = 0;
   out_832953036043329844[38] = 0;
   out_832953036043329844[39] = 0;
   out_832953036043329844[40] = 1;
   out_832953036043329844[41] = 0;
   out_832953036043329844[42] = 0;
   out_832953036043329844[43] = 0;
   out_832953036043329844[44] = 0;
   out_832953036043329844[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_832953036043329844[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_832953036043329844[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_832953036043329844[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_832953036043329844[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_832953036043329844[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_832953036043329844[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_832953036043329844[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_832953036043329844[53] = -9.8100000000000005*dt;
   out_832953036043329844[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_832953036043329844[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_832953036043329844[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_832953036043329844[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_832953036043329844[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_832953036043329844[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_832953036043329844[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_832953036043329844[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_832953036043329844[62] = 0;
   out_832953036043329844[63] = 0;
   out_832953036043329844[64] = 0;
   out_832953036043329844[65] = 0;
   out_832953036043329844[66] = 0;
   out_832953036043329844[67] = 0;
   out_832953036043329844[68] = 0;
   out_832953036043329844[69] = 0;
   out_832953036043329844[70] = 1;
   out_832953036043329844[71] = 0;
   out_832953036043329844[72] = 0;
   out_832953036043329844[73] = 0;
   out_832953036043329844[74] = 0;
   out_832953036043329844[75] = 0;
   out_832953036043329844[76] = 0;
   out_832953036043329844[77] = 0;
   out_832953036043329844[78] = 0;
   out_832953036043329844[79] = 0;
   out_832953036043329844[80] = 1;
}
void h_25(double *state, double *unused, double *out_6217004965884737485) {
   out_6217004965884737485[0] = state[6];
}
void H_25(double *state, double *unused, double *out_2113399649170070232) {
   out_2113399649170070232[0] = 0;
   out_2113399649170070232[1] = 0;
   out_2113399649170070232[2] = 0;
   out_2113399649170070232[3] = 0;
   out_2113399649170070232[4] = 0;
   out_2113399649170070232[5] = 0;
   out_2113399649170070232[6] = 1;
   out_2113399649170070232[7] = 0;
   out_2113399649170070232[8] = 0;
}
void h_24(double *state, double *unused, double *out_724420575405524496) {
   out_724420575405524496[0] = state[4];
   out_724420575405524496[1] = state[5];
}
void H_24(double *state, double *unused, double *out_2755415215857636620) {
   out_2755415215857636620[0] = 0;
   out_2755415215857636620[1] = 0;
   out_2755415215857636620[2] = 0;
   out_2755415215857636620[3] = 0;
   out_2755415215857636620[4] = 1;
   out_2755415215857636620[5] = 0;
   out_2755415215857636620[6] = 0;
   out_2755415215857636620[7] = 0;
   out_2755415215857636620[8] = 0;
   out_2755415215857636620[9] = 0;
   out_2755415215857636620[10] = 0;
   out_2755415215857636620[11] = 0;
   out_2755415215857636620[12] = 0;
   out_2755415215857636620[13] = 0;
   out_2755415215857636620[14] = 1;
   out_2755415215857636620[15] = 0;
   out_2755415215857636620[16] = 0;
   out_2755415215857636620[17] = 0;
}
void h_30(double *state, double *unused, double *out_5458903881474463195) {
   out_5458903881474463195[0] = state[4];
}
void H_30(double *state, double *unused, double *out_2414296680957537966) {
   out_2414296680957537966[0] = 0;
   out_2414296680957537966[1] = 0;
   out_2414296680957537966[2] = 0;
   out_2414296680957537966[3] = 0;
   out_2414296680957537966[4] = 1;
   out_2414296680957537966[5] = 0;
   out_2414296680957537966[6] = 0;
   out_2414296680957537966[7] = 0;
   out_2414296680957537966[8] = 0;
}
void h_26(double *state, double *unused, double *out_7645972956349057858) {
   out_7645972956349057858[0] = state[7];
}
void H_26(double *state, double *unused, double *out_1628103669703985992) {
   out_1628103669703985992[0] = 0;
   out_1628103669703985992[1] = 0;
   out_1628103669703985992[2] = 0;
   out_1628103669703985992[3] = 0;
   out_1628103669703985992[4] = 0;
   out_1628103669703985992[5] = 0;
   out_1628103669703985992[6] = 0;
   out_1628103669703985992[7] = 1;
   out_1628103669703985992[8] = 0;
}
void h_27(double *state, double *unused, double *out_2579304498381259655) {
   out_2579304498381259655[0] = state[3];
}
void H_27(double *state, double *unused, double *out_190702609773594749) {
   out_190702609773594749[0] = 0;
   out_190702609773594749[1] = 0;
   out_190702609773594749[2] = 0;
   out_190702609773594749[3] = 1;
   out_190702609773594749[4] = 0;
   out_190702609773594749[5] = 0;
   out_190702609773594749[6] = 0;
   out_190702609773594749[7] = 0;
   out_190702609773594749[8] = 0;
}
void h_29(double *state, double *unused, double *out_7986166924574242776) {
   out_7986166924574242776[0] = state[1];
}
void H_29(double *state, double *unused, double *out_1904065336643145782) {
   out_1904065336643145782[0] = 0;
   out_1904065336643145782[1] = 1;
   out_1904065336643145782[2] = 0;
   out_1904065336643145782[3] = 0;
   out_1904065336643145782[4] = 0;
   out_1904065336643145782[5] = 0;
   out_1904065336643145782[6] = 0;
   out_1904065336643145782[7] = 0;
   out_1904065336643145782[8] = 0;
}
void h_28(double *state, double *unused, double *out_3819737019032589491) {
   out_3819737019032589491[0] = state[0];
}
void H_28(double *state, double *unused, double *out_6986464353712676356) {
   out_6986464353712676356[0] = 1;
   out_6986464353712676356[1] = 0;
   out_6986464353712676356[2] = 0;
   out_6986464353712676356[3] = 0;
   out_6986464353712676356[4] = 0;
   out_6986464353712676356[5] = 0;
   out_6986464353712676356[6] = 0;
   out_6986464353712676356[7] = 0;
   out_6986464353712676356[8] = 0;
}
void h_31(double *state, double *unused, double *out_6059818297533608340) {
   out_6059818297533608340[0] = state[8];
}
void H_31(double *state, double *unused, double *out_2254311771937337468) {
   out_2254311771937337468[0] = 0;
   out_2254311771937337468[1] = 0;
   out_2254311771937337468[2] = 0;
   out_2254311771937337468[3] = 0;
   out_2254311771937337468[4] = 0;
   out_2254311771937337468[5] = 0;
   out_2254311771937337468[6] = 0;
   out_2254311771937337468[7] = 0;
   out_2254311771937337468[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_395710906661730109) {
  err_fun(nom_x, delta_x, out_395710906661730109);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_6370952191766860566) {
  inv_err_fun(nom_x, true_x, out_6370952191766860566);
}
void car_H_mod_fun(double *state, double *out_8610422609060100183) {
  H_mod_fun(state, out_8610422609060100183);
}
void car_f_fun(double *state, double dt, double *out_7209711513462721716) {
  f_fun(state,  dt, out_7209711513462721716);
}
void car_F_fun(double *state, double dt, double *out_832953036043329844) {
  F_fun(state,  dt, out_832953036043329844);
}
void car_h_25(double *state, double *unused, double *out_6217004965884737485) {
  h_25(state, unused, out_6217004965884737485);
}
void car_H_25(double *state, double *unused, double *out_2113399649170070232) {
  H_25(state, unused, out_2113399649170070232);
}
void car_h_24(double *state, double *unused, double *out_724420575405524496) {
  h_24(state, unused, out_724420575405524496);
}
void car_H_24(double *state, double *unused, double *out_2755415215857636620) {
  H_24(state, unused, out_2755415215857636620);
}
void car_h_30(double *state, double *unused, double *out_5458903881474463195) {
  h_30(state, unused, out_5458903881474463195);
}
void car_H_30(double *state, double *unused, double *out_2414296680957537966) {
  H_30(state, unused, out_2414296680957537966);
}
void car_h_26(double *state, double *unused, double *out_7645972956349057858) {
  h_26(state, unused, out_7645972956349057858);
}
void car_H_26(double *state, double *unused, double *out_1628103669703985992) {
  H_26(state, unused, out_1628103669703985992);
}
void car_h_27(double *state, double *unused, double *out_2579304498381259655) {
  h_27(state, unused, out_2579304498381259655);
}
void car_H_27(double *state, double *unused, double *out_190702609773594749) {
  H_27(state, unused, out_190702609773594749);
}
void car_h_29(double *state, double *unused, double *out_7986166924574242776) {
  h_29(state, unused, out_7986166924574242776);
}
void car_H_29(double *state, double *unused, double *out_1904065336643145782) {
  H_29(state, unused, out_1904065336643145782);
}
void car_h_28(double *state, double *unused, double *out_3819737019032589491) {
  h_28(state, unused, out_3819737019032589491);
}
void car_H_28(double *state, double *unused, double *out_6986464353712676356) {
  H_28(state, unused, out_6986464353712676356);
}
void car_h_31(double *state, double *unused, double *out_6059818297533608340) {
  h_31(state, unused, out_6059818297533608340);
}
void car_H_31(double *state, double *unused, double *out_2254311771937337468) {
  H_31(state, unused, out_2254311771937337468);
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
