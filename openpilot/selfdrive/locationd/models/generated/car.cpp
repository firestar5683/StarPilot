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
void err_fun(double *nom_x, double *delta_x, double *out_8602983957174335298) {
   out_8602983957174335298[0] = delta_x[0] + nom_x[0];
   out_8602983957174335298[1] = delta_x[1] + nom_x[1];
   out_8602983957174335298[2] = delta_x[2] + nom_x[2];
   out_8602983957174335298[3] = delta_x[3] + nom_x[3];
   out_8602983957174335298[4] = delta_x[4] + nom_x[4];
   out_8602983957174335298[5] = delta_x[5] + nom_x[5];
   out_8602983957174335298[6] = delta_x[6] + nom_x[6];
   out_8602983957174335298[7] = delta_x[7] + nom_x[7];
   out_8602983957174335298[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_6809988399191804319) {
   out_6809988399191804319[0] = -nom_x[0] + true_x[0];
   out_6809988399191804319[1] = -nom_x[1] + true_x[1];
   out_6809988399191804319[2] = -nom_x[2] + true_x[2];
   out_6809988399191804319[3] = -nom_x[3] + true_x[3];
   out_6809988399191804319[4] = -nom_x[4] + true_x[4];
   out_6809988399191804319[5] = -nom_x[5] + true_x[5];
   out_6809988399191804319[6] = -nom_x[6] + true_x[6];
   out_6809988399191804319[7] = -nom_x[7] + true_x[7];
   out_6809988399191804319[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_883537812237458096) {
   out_883537812237458096[0] = 1.0;
   out_883537812237458096[1] = 0.0;
   out_883537812237458096[2] = 0.0;
   out_883537812237458096[3] = 0.0;
   out_883537812237458096[4] = 0.0;
   out_883537812237458096[5] = 0.0;
   out_883537812237458096[6] = 0.0;
   out_883537812237458096[7] = 0.0;
   out_883537812237458096[8] = 0.0;
   out_883537812237458096[9] = 0.0;
   out_883537812237458096[10] = 1.0;
   out_883537812237458096[11] = 0.0;
   out_883537812237458096[12] = 0.0;
   out_883537812237458096[13] = 0.0;
   out_883537812237458096[14] = 0.0;
   out_883537812237458096[15] = 0.0;
   out_883537812237458096[16] = 0.0;
   out_883537812237458096[17] = 0.0;
   out_883537812237458096[18] = 0.0;
   out_883537812237458096[19] = 0.0;
   out_883537812237458096[20] = 1.0;
   out_883537812237458096[21] = 0.0;
   out_883537812237458096[22] = 0.0;
   out_883537812237458096[23] = 0.0;
   out_883537812237458096[24] = 0.0;
   out_883537812237458096[25] = 0.0;
   out_883537812237458096[26] = 0.0;
   out_883537812237458096[27] = 0.0;
   out_883537812237458096[28] = 0.0;
   out_883537812237458096[29] = 0.0;
   out_883537812237458096[30] = 1.0;
   out_883537812237458096[31] = 0.0;
   out_883537812237458096[32] = 0.0;
   out_883537812237458096[33] = 0.0;
   out_883537812237458096[34] = 0.0;
   out_883537812237458096[35] = 0.0;
   out_883537812237458096[36] = 0.0;
   out_883537812237458096[37] = 0.0;
   out_883537812237458096[38] = 0.0;
   out_883537812237458096[39] = 0.0;
   out_883537812237458096[40] = 1.0;
   out_883537812237458096[41] = 0.0;
   out_883537812237458096[42] = 0.0;
   out_883537812237458096[43] = 0.0;
   out_883537812237458096[44] = 0.0;
   out_883537812237458096[45] = 0.0;
   out_883537812237458096[46] = 0.0;
   out_883537812237458096[47] = 0.0;
   out_883537812237458096[48] = 0.0;
   out_883537812237458096[49] = 0.0;
   out_883537812237458096[50] = 1.0;
   out_883537812237458096[51] = 0.0;
   out_883537812237458096[52] = 0.0;
   out_883537812237458096[53] = 0.0;
   out_883537812237458096[54] = 0.0;
   out_883537812237458096[55] = 0.0;
   out_883537812237458096[56] = 0.0;
   out_883537812237458096[57] = 0.0;
   out_883537812237458096[58] = 0.0;
   out_883537812237458096[59] = 0.0;
   out_883537812237458096[60] = 1.0;
   out_883537812237458096[61] = 0.0;
   out_883537812237458096[62] = 0.0;
   out_883537812237458096[63] = 0.0;
   out_883537812237458096[64] = 0.0;
   out_883537812237458096[65] = 0.0;
   out_883537812237458096[66] = 0.0;
   out_883537812237458096[67] = 0.0;
   out_883537812237458096[68] = 0.0;
   out_883537812237458096[69] = 0.0;
   out_883537812237458096[70] = 1.0;
   out_883537812237458096[71] = 0.0;
   out_883537812237458096[72] = 0.0;
   out_883537812237458096[73] = 0.0;
   out_883537812237458096[74] = 0.0;
   out_883537812237458096[75] = 0.0;
   out_883537812237458096[76] = 0.0;
   out_883537812237458096[77] = 0.0;
   out_883537812237458096[78] = 0.0;
   out_883537812237458096[79] = 0.0;
   out_883537812237458096[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_2449018896263561698) {
   out_2449018896263561698[0] = state[0];
   out_2449018896263561698[1] = state[1];
   out_2449018896263561698[2] = state[2];
   out_2449018896263561698[3] = state[3];
   out_2449018896263561698[4] = state[4];
   out_2449018896263561698[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_2449018896263561698[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_2449018896263561698[7] = state[7];
   out_2449018896263561698[8] = state[8];
}
void F_fun(double *state, double dt, double *out_9184524155541408120) {
   out_9184524155541408120[0] = 1;
   out_9184524155541408120[1] = 0;
   out_9184524155541408120[2] = 0;
   out_9184524155541408120[3] = 0;
   out_9184524155541408120[4] = 0;
   out_9184524155541408120[5] = 0;
   out_9184524155541408120[6] = 0;
   out_9184524155541408120[7] = 0;
   out_9184524155541408120[8] = 0;
   out_9184524155541408120[9] = 0;
   out_9184524155541408120[10] = 1;
   out_9184524155541408120[11] = 0;
   out_9184524155541408120[12] = 0;
   out_9184524155541408120[13] = 0;
   out_9184524155541408120[14] = 0;
   out_9184524155541408120[15] = 0;
   out_9184524155541408120[16] = 0;
   out_9184524155541408120[17] = 0;
   out_9184524155541408120[18] = 0;
   out_9184524155541408120[19] = 0;
   out_9184524155541408120[20] = 1;
   out_9184524155541408120[21] = 0;
   out_9184524155541408120[22] = 0;
   out_9184524155541408120[23] = 0;
   out_9184524155541408120[24] = 0;
   out_9184524155541408120[25] = 0;
   out_9184524155541408120[26] = 0;
   out_9184524155541408120[27] = 0;
   out_9184524155541408120[28] = 0;
   out_9184524155541408120[29] = 0;
   out_9184524155541408120[30] = 1;
   out_9184524155541408120[31] = 0;
   out_9184524155541408120[32] = 0;
   out_9184524155541408120[33] = 0;
   out_9184524155541408120[34] = 0;
   out_9184524155541408120[35] = 0;
   out_9184524155541408120[36] = 0;
   out_9184524155541408120[37] = 0;
   out_9184524155541408120[38] = 0;
   out_9184524155541408120[39] = 0;
   out_9184524155541408120[40] = 1;
   out_9184524155541408120[41] = 0;
   out_9184524155541408120[42] = 0;
   out_9184524155541408120[43] = 0;
   out_9184524155541408120[44] = 0;
   out_9184524155541408120[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_9184524155541408120[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_9184524155541408120[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_9184524155541408120[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_9184524155541408120[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_9184524155541408120[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_9184524155541408120[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_9184524155541408120[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_9184524155541408120[53] = -9.8100000000000005*dt;
   out_9184524155541408120[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_9184524155541408120[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_9184524155541408120[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_9184524155541408120[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_9184524155541408120[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_9184524155541408120[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_9184524155541408120[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_9184524155541408120[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_9184524155541408120[62] = 0;
   out_9184524155541408120[63] = 0;
   out_9184524155541408120[64] = 0;
   out_9184524155541408120[65] = 0;
   out_9184524155541408120[66] = 0;
   out_9184524155541408120[67] = 0;
   out_9184524155541408120[68] = 0;
   out_9184524155541408120[69] = 0;
   out_9184524155541408120[70] = 1;
   out_9184524155541408120[71] = 0;
   out_9184524155541408120[72] = 0;
   out_9184524155541408120[73] = 0;
   out_9184524155541408120[74] = 0;
   out_9184524155541408120[75] = 0;
   out_9184524155541408120[76] = 0;
   out_9184524155541408120[77] = 0;
   out_9184524155541408120[78] = 0;
   out_9184524155541408120[79] = 0;
   out_9184524155541408120[80] = 1;
}
void h_25(double *state, double *unused, double *out_3274704919583746110) {
   out_3274704919583746110[0] = state[6];
}
void H_25(double *state, double *unused, double *out_6928939238479605978) {
   out_6928939238479605978[0] = 0;
   out_6928939238479605978[1] = 0;
   out_6928939238479605978[2] = 0;
   out_6928939238479605978[3] = 0;
   out_6928939238479605978[4] = 0;
   out_6928939238479605978[5] = 0;
   out_6928939238479605978[6] = 1;
   out_6928939238479605978[7] = 0;
   out_6928939238479605978[8] = 0;
}
void h_24(double *state, double *unused, double *out_4314296844222658784) {
   out_4314296844222658784[0] = state[4];
   out_4314296844222658784[1] = state[5];
}
void H_24(double *state, double *unused, double *out_6083942629695910579) {
   out_6083942629695910579[0] = 0;
   out_6083942629695910579[1] = 0;
   out_6083942629695910579[2] = 0;
   out_6083942629695910579[3] = 0;
   out_6083942629695910579[4] = 1;
   out_6083942629695910579[5] = 0;
   out_6083942629695910579[6] = 0;
   out_6083942629695910579[7] = 0;
   out_6083942629695910579[8] = 0;
   out_6083942629695910579[9] = 0;
   out_6083942629695910579[10] = 0;
   out_6083942629695910579[11] = 0;
   out_6083942629695910579[12] = 0;
   out_6083942629695910579[13] = 0;
   out_6083942629695910579[14] = 1;
   out_6083942629695910579[15] = 0;
   out_6083942629695910579[16] = 0;
   out_6083942629695910579[17] = 0;
}
void h_30(double *state, double *unused, double *out_5365172557134795774) {
   out_5365172557134795774[0] = state[4];
}
void H_30(double *state, double *unused, double *out_4410606279972357351) {
   out_4410606279972357351[0] = 0;
   out_4410606279972357351[1] = 0;
   out_4410606279972357351[2] = 0;
   out_4410606279972357351[3] = 0;
   out_4410606279972357351[4] = 1;
   out_4410606279972357351[5] = 0;
   out_4410606279972357351[6] = 0;
   out_4410606279972357351[7] = 0;
   out_4410606279972357351[8] = 0;
}
void h_26(double *state, double *unused, double *out_2552620453864942391) {
   out_2552620453864942391[0] = state[7];
}
void H_26(double *state, double *unused, double *out_7776301516355889414) {
   out_7776301516355889414[0] = 0;
   out_7776301516355889414[1] = 0;
   out_7776301516355889414[2] = 0;
   out_7776301516355889414[3] = 0;
   out_7776301516355889414[4] = 0;
   out_7776301516355889414[5] = 0;
   out_7776301516355889414[6] = 0;
   out_7776301516355889414[7] = 1;
   out_7776301516355889414[8] = 0;
}
void h_27(double *state, double *unused, double *out_4256789012919044222) {
   out_4256789012919044222[0] = state[3];
}
void H_27(double *state, double *unused, double *out_2187012208788414134) {
   out_2187012208788414134[0] = 0;
   out_2187012208788414134[1] = 0;
   out_2187012208788414134[2] = 0;
   out_2187012208788414134[3] = 1;
   out_2187012208788414134[4] = 0;
   out_2187012208788414134[5] = 0;
   out_2187012208788414134[6] = 0;
   out_2187012208788414134[7] = 0;
   out_2187012208788414134[8] = 0;
}
void h_29(double *state, double *unused, double *out_513112930423919314) {
   out_513112930423919314[0] = state[1];
}
void H_29(double *state, double *unused, double *out_3900374935657965167) {
   out_3900374935657965167[0] = 0;
   out_3900374935657965167[1] = 1;
   out_3900374935657965167[2] = 0;
   out_3900374935657965167[3] = 0;
   out_3900374935657965167[4] = 0;
   out_3900374935657965167[5] = 0;
   out_3900374935657965167[6] = 0;
   out_3900374935657965167[7] = 0;
   out_3900374935657965167[8] = 0;
}
void h_28(double *state, double *unused, double *out_4860104897595521739) {
   out_4860104897595521739[0] = state[0];
}
void H_28(double *state, double *unused, double *out_8982773952727495741) {
   out_8982773952727495741[0] = 1;
   out_8982773952727495741[1] = 0;
   out_8982773952727495741[2] = 0;
   out_8982773952727495741[3] = 0;
   out_8982773952727495741[4] = 0;
   out_8982773952727495741[5] = 0;
   out_8982773952727495741[6] = 0;
   out_8982773952727495741[7] = 0;
   out_8982773952727495741[8] = 0;
}
void h_31(double *state, double *unused, double *out_2999510857299240221) {
   out_2999510857299240221[0] = state[8];
}
void H_31(double *state, double *unused, double *out_6898293276602645550) {
   out_6898293276602645550[0] = 0;
   out_6898293276602645550[1] = 0;
   out_6898293276602645550[2] = 0;
   out_6898293276602645550[3] = 0;
   out_6898293276602645550[4] = 0;
   out_6898293276602645550[5] = 0;
   out_6898293276602645550[6] = 0;
   out_6898293276602645550[7] = 0;
   out_6898293276602645550[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_8602983957174335298) {
  err_fun(nom_x, delta_x, out_8602983957174335298);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_6809988399191804319) {
  inv_err_fun(nom_x, true_x, out_6809988399191804319);
}
void car_H_mod_fun(double *state, double *out_883537812237458096) {
  H_mod_fun(state, out_883537812237458096);
}
void car_f_fun(double *state, double dt, double *out_2449018896263561698) {
  f_fun(state,  dt, out_2449018896263561698);
}
void car_F_fun(double *state, double dt, double *out_9184524155541408120) {
  F_fun(state,  dt, out_9184524155541408120);
}
void car_h_25(double *state, double *unused, double *out_3274704919583746110) {
  h_25(state, unused, out_3274704919583746110);
}
void car_H_25(double *state, double *unused, double *out_6928939238479605978) {
  H_25(state, unused, out_6928939238479605978);
}
void car_h_24(double *state, double *unused, double *out_4314296844222658784) {
  h_24(state, unused, out_4314296844222658784);
}
void car_H_24(double *state, double *unused, double *out_6083942629695910579) {
  H_24(state, unused, out_6083942629695910579);
}
void car_h_30(double *state, double *unused, double *out_5365172557134795774) {
  h_30(state, unused, out_5365172557134795774);
}
void car_H_30(double *state, double *unused, double *out_4410606279972357351) {
  H_30(state, unused, out_4410606279972357351);
}
void car_h_26(double *state, double *unused, double *out_2552620453864942391) {
  h_26(state, unused, out_2552620453864942391);
}
void car_H_26(double *state, double *unused, double *out_7776301516355889414) {
  H_26(state, unused, out_7776301516355889414);
}
void car_h_27(double *state, double *unused, double *out_4256789012919044222) {
  h_27(state, unused, out_4256789012919044222);
}
void car_H_27(double *state, double *unused, double *out_2187012208788414134) {
  H_27(state, unused, out_2187012208788414134);
}
void car_h_29(double *state, double *unused, double *out_513112930423919314) {
  h_29(state, unused, out_513112930423919314);
}
void car_H_29(double *state, double *unused, double *out_3900374935657965167) {
  H_29(state, unused, out_3900374935657965167);
}
void car_h_28(double *state, double *unused, double *out_4860104897595521739) {
  h_28(state, unused, out_4860104897595521739);
}
void car_H_28(double *state, double *unused, double *out_8982773952727495741) {
  H_28(state, unused, out_8982773952727495741);
}
void car_h_31(double *state, double *unused, double *out_2999510857299240221) {
  h_31(state, unused, out_2999510857299240221);
}
void car_H_31(double *state, double *unused, double *out_6898293276602645550) {
  H_31(state, unused, out_6898293276602645550);
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
