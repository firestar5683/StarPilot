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
void err_fun(double *nom_x, double *delta_x, double *out_3908090119423544709) {
   out_3908090119423544709[0] = delta_x[0] + nom_x[0];
   out_3908090119423544709[1] = delta_x[1] + nom_x[1];
   out_3908090119423544709[2] = delta_x[2] + nom_x[2];
   out_3908090119423544709[3] = delta_x[3] + nom_x[3];
   out_3908090119423544709[4] = delta_x[4] + nom_x[4];
   out_3908090119423544709[5] = delta_x[5] + nom_x[5];
   out_3908090119423544709[6] = delta_x[6] + nom_x[6];
   out_3908090119423544709[7] = delta_x[7] + nom_x[7];
   out_3908090119423544709[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_94487865813143080) {
   out_94487865813143080[0] = -nom_x[0] + true_x[0];
   out_94487865813143080[1] = -nom_x[1] + true_x[1];
   out_94487865813143080[2] = -nom_x[2] + true_x[2];
   out_94487865813143080[3] = -nom_x[3] + true_x[3];
   out_94487865813143080[4] = -nom_x[4] + true_x[4];
   out_94487865813143080[5] = -nom_x[5] + true_x[5];
   out_94487865813143080[6] = -nom_x[6] + true_x[6];
   out_94487865813143080[7] = -nom_x[7] + true_x[7];
   out_94487865813143080[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_6883866144239101093) {
   out_6883866144239101093[0] = 1.0;
   out_6883866144239101093[1] = 0.0;
   out_6883866144239101093[2] = 0.0;
   out_6883866144239101093[3] = 0.0;
   out_6883866144239101093[4] = 0.0;
   out_6883866144239101093[5] = 0.0;
   out_6883866144239101093[6] = 0.0;
   out_6883866144239101093[7] = 0.0;
   out_6883866144239101093[8] = 0.0;
   out_6883866144239101093[9] = 0.0;
   out_6883866144239101093[10] = 1.0;
   out_6883866144239101093[11] = 0.0;
   out_6883866144239101093[12] = 0.0;
   out_6883866144239101093[13] = 0.0;
   out_6883866144239101093[14] = 0.0;
   out_6883866144239101093[15] = 0.0;
   out_6883866144239101093[16] = 0.0;
   out_6883866144239101093[17] = 0.0;
   out_6883866144239101093[18] = 0.0;
   out_6883866144239101093[19] = 0.0;
   out_6883866144239101093[20] = 1.0;
   out_6883866144239101093[21] = 0.0;
   out_6883866144239101093[22] = 0.0;
   out_6883866144239101093[23] = 0.0;
   out_6883866144239101093[24] = 0.0;
   out_6883866144239101093[25] = 0.0;
   out_6883866144239101093[26] = 0.0;
   out_6883866144239101093[27] = 0.0;
   out_6883866144239101093[28] = 0.0;
   out_6883866144239101093[29] = 0.0;
   out_6883866144239101093[30] = 1.0;
   out_6883866144239101093[31] = 0.0;
   out_6883866144239101093[32] = 0.0;
   out_6883866144239101093[33] = 0.0;
   out_6883866144239101093[34] = 0.0;
   out_6883866144239101093[35] = 0.0;
   out_6883866144239101093[36] = 0.0;
   out_6883866144239101093[37] = 0.0;
   out_6883866144239101093[38] = 0.0;
   out_6883866144239101093[39] = 0.0;
   out_6883866144239101093[40] = 1.0;
   out_6883866144239101093[41] = 0.0;
   out_6883866144239101093[42] = 0.0;
   out_6883866144239101093[43] = 0.0;
   out_6883866144239101093[44] = 0.0;
   out_6883866144239101093[45] = 0.0;
   out_6883866144239101093[46] = 0.0;
   out_6883866144239101093[47] = 0.0;
   out_6883866144239101093[48] = 0.0;
   out_6883866144239101093[49] = 0.0;
   out_6883866144239101093[50] = 1.0;
   out_6883866144239101093[51] = 0.0;
   out_6883866144239101093[52] = 0.0;
   out_6883866144239101093[53] = 0.0;
   out_6883866144239101093[54] = 0.0;
   out_6883866144239101093[55] = 0.0;
   out_6883866144239101093[56] = 0.0;
   out_6883866144239101093[57] = 0.0;
   out_6883866144239101093[58] = 0.0;
   out_6883866144239101093[59] = 0.0;
   out_6883866144239101093[60] = 1.0;
   out_6883866144239101093[61] = 0.0;
   out_6883866144239101093[62] = 0.0;
   out_6883866144239101093[63] = 0.0;
   out_6883866144239101093[64] = 0.0;
   out_6883866144239101093[65] = 0.0;
   out_6883866144239101093[66] = 0.0;
   out_6883866144239101093[67] = 0.0;
   out_6883866144239101093[68] = 0.0;
   out_6883866144239101093[69] = 0.0;
   out_6883866144239101093[70] = 1.0;
   out_6883866144239101093[71] = 0.0;
   out_6883866144239101093[72] = 0.0;
   out_6883866144239101093[73] = 0.0;
   out_6883866144239101093[74] = 0.0;
   out_6883866144239101093[75] = 0.0;
   out_6883866144239101093[76] = 0.0;
   out_6883866144239101093[77] = 0.0;
   out_6883866144239101093[78] = 0.0;
   out_6883866144239101093[79] = 0.0;
   out_6883866144239101093[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_6768278951699235134) {
   out_6768278951699235134[0] = state[0];
   out_6768278951699235134[1] = state[1];
   out_6768278951699235134[2] = state[2];
   out_6768278951699235134[3] = state[3];
   out_6768278951699235134[4] = state[4];
   out_6768278951699235134[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_6768278951699235134[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_6768278951699235134[7] = state[7];
   out_6768278951699235134[8] = state[8];
}
void F_fun(double *state, double dt, double *out_1909506188347403111) {
   out_1909506188347403111[0] = 1;
   out_1909506188347403111[1] = 0;
   out_1909506188347403111[2] = 0;
   out_1909506188347403111[3] = 0;
   out_1909506188347403111[4] = 0;
   out_1909506188347403111[5] = 0;
   out_1909506188347403111[6] = 0;
   out_1909506188347403111[7] = 0;
   out_1909506188347403111[8] = 0;
   out_1909506188347403111[9] = 0;
   out_1909506188347403111[10] = 1;
   out_1909506188347403111[11] = 0;
   out_1909506188347403111[12] = 0;
   out_1909506188347403111[13] = 0;
   out_1909506188347403111[14] = 0;
   out_1909506188347403111[15] = 0;
   out_1909506188347403111[16] = 0;
   out_1909506188347403111[17] = 0;
   out_1909506188347403111[18] = 0;
   out_1909506188347403111[19] = 0;
   out_1909506188347403111[20] = 1;
   out_1909506188347403111[21] = 0;
   out_1909506188347403111[22] = 0;
   out_1909506188347403111[23] = 0;
   out_1909506188347403111[24] = 0;
   out_1909506188347403111[25] = 0;
   out_1909506188347403111[26] = 0;
   out_1909506188347403111[27] = 0;
   out_1909506188347403111[28] = 0;
   out_1909506188347403111[29] = 0;
   out_1909506188347403111[30] = 1;
   out_1909506188347403111[31] = 0;
   out_1909506188347403111[32] = 0;
   out_1909506188347403111[33] = 0;
   out_1909506188347403111[34] = 0;
   out_1909506188347403111[35] = 0;
   out_1909506188347403111[36] = 0;
   out_1909506188347403111[37] = 0;
   out_1909506188347403111[38] = 0;
   out_1909506188347403111[39] = 0;
   out_1909506188347403111[40] = 1;
   out_1909506188347403111[41] = 0;
   out_1909506188347403111[42] = 0;
   out_1909506188347403111[43] = 0;
   out_1909506188347403111[44] = 0;
   out_1909506188347403111[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_1909506188347403111[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_1909506188347403111[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_1909506188347403111[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_1909506188347403111[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_1909506188347403111[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_1909506188347403111[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_1909506188347403111[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_1909506188347403111[53] = -9.8100000000000005*dt;
   out_1909506188347403111[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_1909506188347403111[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_1909506188347403111[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_1909506188347403111[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_1909506188347403111[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_1909506188347403111[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_1909506188347403111[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_1909506188347403111[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_1909506188347403111[62] = 0;
   out_1909506188347403111[63] = 0;
   out_1909506188347403111[64] = 0;
   out_1909506188347403111[65] = 0;
   out_1909506188347403111[66] = 0;
   out_1909506188347403111[67] = 0;
   out_1909506188347403111[68] = 0;
   out_1909506188347403111[69] = 0;
   out_1909506188347403111[70] = 1;
   out_1909506188347403111[71] = 0;
   out_1909506188347403111[72] = 0;
   out_1909506188347403111[73] = 0;
   out_1909506188347403111[74] = 0;
   out_1909506188347403111[75] = 0;
   out_1909506188347403111[76] = 0;
   out_1909506188347403111[77] = 0;
   out_1909506188347403111[78] = 0;
   out_1909506188347403111[79] = 0;
   out_1909506188347403111[80] = 1;
}
void h_25(double *state, double *unused, double *out_6576153234371669373) {
   out_6576153234371669373[0] = state[6];
}
void H_25(double *state, double *unused, double *out_6659186104285785683) {
   out_6659186104285785683[0] = 0;
   out_6659186104285785683[1] = 0;
   out_6659186104285785683[2] = 0;
   out_6659186104285785683[3] = 0;
   out_6659186104285785683[4] = 0;
   out_6659186104285785683[5] = 0;
   out_6659186104285785683[6] = 1;
   out_6659186104285785683[7] = 0;
   out_6659186104285785683[8] = 0;
}
void h_24(double *state, double *unused, double *out_3352365815627571869) {
   out_3352365815627571869[0] = state[4];
   out_3352365815627571869[1] = state[5];
}
void H_24(double *state, double *unused, double *out_7055831408639645178) {
   out_7055831408639645178[0] = 0;
   out_7055831408639645178[1] = 0;
   out_7055831408639645178[2] = 0;
   out_7055831408639645178[3] = 0;
   out_7055831408639645178[4] = 1;
   out_7055831408639645178[5] = 0;
   out_7055831408639645178[6] = 0;
   out_7055831408639645178[7] = 0;
   out_7055831408639645178[8] = 0;
   out_7055831408639645178[9] = 0;
   out_7055831408639645178[10] = 0;
   out_7055831408639645178[11] = 0;
   out_7055831408639645178[12] = 0;
   out_7055831408639645178[13] = 0;
   out_7055831408639645178[14] = 1;
   out_7055831408639645178[15] = 0;
   out_7055831408639645178[16] = 0;
   out_7055831408639645178[17] = 0;
}
void h_30(double *state, double *unused, double *out_8233141311083859893) {
   out_8233141311083859893[0] = state[4];
}
void H_30(double *state, double *unused, double *out_4140853145778537056) {
   out_4140853145778537056[0] = 0;
   out_4140853145778537056[1] = 0;
   out_4140853145778537056[2] = 0;
   out_4140853145778537056[3] = 0;
   out_4140853145778537056[4] = 1;
   out_4140853145778537056[5] = 0;
   out_4140853145778537056[6] = 0;
   out_4140853145778537056[7] = 0;
   out_4140853145778537056[8] = 0;
}
void h_26(double *state, double *unused, double *out_7065397510007718156) {
   out_7065397510007718156[0] = state[7];
}
void H_26(double *state, double *unused, double *out_3354660134524985082) {
   out_3354660134524985082[0] = 0;
   out_3354660134524985082[1] = 0;
   out_3354660134524985082[2] = 0;
   out_3354660134524985082[3] = 0;
   out_3354660134524985082[4] = 0;
   out_3354660134524985082[5] = 0;
   out_3354660134524985082[6] = 0;
   out_3354660134524985082[7] = 1;
   out_3354660134524985082[8] = 0;
}
void h_27(double *state, double *unused, double *out_858990200057031440) {
   out_858990200057031440[0] = state[3];
}
void H_27(double *state, double *unused, double *out_1917259074594593839) {
   out_1917259074594593839[0] = 0;
   out_1917259074594593839[1] = 0;
   out_1917259074594593839[2] = 0;
   out_1917259074594593839[3] = 1;
   out_1917259074594593839[4] = 0;
   out_1917259074594593839[5] = 0;
   out_1917259074594593839[6] = 0;
   out_1917259074594593839[7] = 0;
   out_1917259074594593839[8] = 0;
}
void h_29(double *state, double *unused, double *out_583796137772525551) {
   out_583796137772525551[0] = state[1];
}
void H_29(double *state, double *unused, double *out_3630621801464144872) {
   out_3630621801464144872[0] = 0;
   out_3630621801464144872[1] = 1;
   out_3630621801464144872[2] = 0;
   out_3630621801464144872[3] = 0;
   out_3630621801464144872[4] = 0;
   out_3630621801464144872[5] = 0;
   out_3630621801464144872[6] = 0;
   out_3630621801464144872[7] = 0;
   out_3630621801464144872[8] = 0;
}
void h_28(double *state, double *unused, double *out_8161553212383445002) {
   out_8161553212383445002[0] = state[0];
}
void H_28(double *state, double *unused, double *out_8713020818533675446) {
   out_8713020818533675446[0] = 1;
   out_8713020818533675446[1] = 0;
   out_8713020818533675446[2] = 0;
   out_8713020818533675446[3] = 0;
   out_8713020818533675446[4] = 0;
   out_8713020818533675446[5] = 0;
   out_8713020818533675446[6] = 0;
   out_8713020818533675446[7] = 0;
   out_8713020818533675446[8] = 0;
}
void h_31(double *state, double *unused, double *out_6300959172087163484) {
   out_6300959172087163484[0] = state[8];
}
void H_31(double *state, double *unused, double *out_417489146226031570) {
   out_417489146226031570[0] = 0;
   out_417489146226031570[1] = 0;
   out_417489146226031570[2] = 0;
   out_417489146226031570[3] = 0;
   out_417489146226031570[4] = 0;
   out_417489146226031570[5] = 0;
   out_417489146226031570[6] = 0;
   out_417489146226031570[7] = 0;
   out_417489146226031570[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_3908090119423544709) {
  err_fun(nom_x, delta_x, out_3908090119423544709);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_94487865813143080) {
  inv_err_fun(nom_x, true_x, out_94487865813143080);
}
void car_H_mod_fun(double *state, double *out_6883866144239101093) {
  H_mod_fun(state, out_6883866144239101093);
}
void car_f_fun(double *state, double dt, double *out_6768278951699235134) {
  f_fun(state,  dt, out_6768278951699235134);
}
void car_F_fun(double *state, double dt, double *out_1909506188347403111) {
  F_fun(state,  dt, out_1909506188347403111);
}
void car_h_25(double *state, double *unused, double *out_6576153234371669373) {
  h_25(state, unused, out_6576153234371669373);
}
void car_H_25(double *state, double *unused, double *out_6659186104285785683) {
  H_25(state, unused, out_6659186104285785683);
}
void car_h_24(double *state, double *unused, double *out_3352365815627571869) {
  h_24(state, unused, out_3352365815627571869);
}
void car_H_24(double *state, double *unused, double *out_7055831408639645178) {
  H_24(state, unused, out_7055831408639645178);
}
void car_h_30(double *state, double *unused, double *out_8233141311083859893) {
  h_30(state, unused, out_8233141311083859893);
}
void car_H_30(double *state, double *unused, double *out_4140853145778537056) {
  H_30(state, unused, out_4140853145778537056);
}
void car_h_26(double *state, double *unused, double *out_7065397510007718156) {
  h_26(state, unused, out_7065397510007718156);
}
void car_H_26(double *state, double *unused, double *out_3354660134524985082) {
  H_26(state, unused, out_3354660134524985082);
}
void car_h_27(double *state, double *unused, double *out_858990200057031440) {
  h_27(state, unused, out_858990200057031440);
}
void car_H_27(double *state, double *unused, double *out_1917259074594593839) {
  H_27(state, unused, out_1917259074594593839);
}
void car_h_29(double *state, double *unused, double *out_583796137772525551) {
  h_29(state, unused, out_583796137772525551);
}
void car_H_29(double *state, double *unused, double *out_3630621801464144872) {
  H_29(state, unused, out_3630621801464144872);
}
void car_h_28(double *state, double *unused, double *out_8161553212383445002) {
  h_28(state, unused, out_8161553212383445002);
}
void car_H_28(double *state, double *unused, double *out_8713020818533675446) {
  H_28(state, unused, out_8713020818533675446);
}
void car_h_31(double *state, double *unused, double *out_6300959172087163484) {
  h_31(state, unused, out_6300959172087163484);
}
void car_H_31(double *state, double *unused, double *out_417489146226031570) {
  H_31(state, unused, out_417489146226031570);
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
