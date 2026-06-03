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
void err_fun(double *nom_x, double *delta_x, double *out_6018065189512211380) {
   out_6018065189512211380[0] = delta_x[0] + nom_x[0];
   out_6018065189512211380[1] = delta_x[1] + nom_x[1];
   out_6018065189512211380[2] = delta_x[2] + nom_x[2];
   out_6018065189512211380[3] = delta_x[3] + nom_x[3];
   out_6018065189512211380[4] = delta_x[4] + nom_x[4];
   out_6018065189512211380[5] = delta_x[5] + nom_x[5];
   out_6018065189512211380[6] = delta_x[6] + nom_x[6];
   out_6018065189512211380[7] = delta_x[7] + nom_x[7];
   out_6018065189512211380[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_1095263434101283480) {
   out_1095263434101283480[0] = -nom_x[0] + true_x[0];
   out_1095263434101283480[1] = -nom_x[1] + true_x[1];
   out_1095263434101283480[2] = -nom_x[2] + true_x[2];
   out_1095263434101283480[3] = -nom_x[3] + true_x[3];
   out_1095263434101283480[4] = -nom_x[4] + true_x[4];
   out_1095263434101283480[5] = -nom_x[5] + true_x[5];
   out_1095263434101283480[6] = -nom_x[6] + true_x[6];
   out_1095263434101283480[7] = -nom_x[7] + true_x[7];
   out_1095263434101283480[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_2728844015902940614) {
   out_2728844015902940614[0] = 1.0;
   out_2728844015902940614[1] = 0.0;
   out_2728844015902940614[2] = 0.0;
   out_2728844015902940614[3] = 0.0;
   out_2728844015902940614[4] = 0.0;
   out_2728844015902940614[5] = 0.0;
   out_2728844015902940614[6] = 0.0;
   out_2728844015902940614[7] = 0.0;
   out_2728844015902940614[8] = 0.0;
   out_2728844015902940614[9] = 0.0;
   out_2728844015902940614[10] = 1.0;
   out_2728844015902940614[11] = 0.0;
   out_2728844015902940614[12] = 0.0;
   out_2728844015902940614[13] = 0.0;
   out_2728844015902940614[14] = 0.0;
   out_2728844015902940614[15] = 0.0;
   out_2728844015902940614[16] = 0.0;
   out_2728844015902940614[17] = 0.0;
   out_2728844015902940614[18] = 0.0;
   out_2728844015902940614[19] = 0.0;
   out_2728844015902940614[20] = 1.0;
   out_2728844015902940614[21] = 0.0;
   out_2728844015902940614[22] = 0.0;
   out_2728844015902940614[23] = 0.0;
   out_2728844015902940614[24] = 0.0;
   out_2728844015902940614[25] = 0.0;
   out_2728844015902940614[26] = 0.0;
   out_2728844015902940614[27] = 0.0;
   out_2728844015902940614[28] = 0.0;
   out_2728844015902940614[29] = 0.0;
   out_2728844015902940614[30] = 1.0;
   out_2728844015902940614[31] = 0.0;
   out_2728844015902940614[32] = 0.0;
   out_2728844015902940614[33] = 0.0;
   out_2728844015902940614[34] = 0.0;
   out_2728844015902940614[35] = 0.0;
   out_2728844015902940614[36] = 0.0;
   out_2728844015902940614[37] = 0.0;
   out_2728844015902940614[38] = 0.0;
   out_2728844015902940614[39] = 0.0;
   out_2728844015902940614[40] = 1.0;
   out_2728844015902940614[41] = 0.0;
   out_2728844015902940614[42] = 0.0;
   out_2728844015902940614[43] = 0.0;
   out_2728844015902940614[44] = 0.0;
   out_2728844015902940614[45] = 0.0;
   out_2728844015902940614[46] = 0.0;
   out_2728844015902940614[47] = 0.0;
   out_2728844015902940614[48] = 0.0;
   out_2728844015902940614[49] = 0.0;
   out_2728844015902940614[50] = 1.0;
   out_2728844015902940614[51] = 0.0;
   out_2728844015902940614[52] = 0.0;
   out_2728844015902940614[53] = 0.0;
   out_2728844015902940614[54] = 0.0;
   out_2728844015902940614[55] = 0.0;
   out_2728844015902940614[56] = 0.0;
   out_2728844015902940614[57] = 0.0;
   out_2728844015902940614[58] = 0.0;
   out_2728844015902940614[59] = 0.0;
   out_2728844015902940614[60] = 1.0;
   out_2728844015902940614[61] = 0.0;
   out_2728844015902940614[62] = 0.0;
   out_2728844015902940614[63] = 0.0;
   out_2728844015902940614[64] = 0.0;
   out_2728844015902940614[65] = 0.0;
   out_2728844015902940614[66] = 0.0;
   out_2728844015902940614[67] = 0.0;
   out_2728844015902940614[68] = 0.0;
   out_2728844015902940614[69] = 0.0;
   out_2728844015902940614[70] = 1.0;
   out_2728844015902940614[71] = 0.0;
   out_2728844015902940614[72] = 0.0;
   out_2728844015902940614[73] = 0.0;
   out_2728844015902940614[74] = 0.0;
   out_2728844015902940614[75] = 0.0;
   out_2728844015902940614[76] = 0.0;
   out_2728844015902940614[77] = 0.0;
   out_2728844015902940614[78] = 0.0;
   out_2728844015902940614[79] = 0.0;
   out_2728844015902940614[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_6525929466162239676) {
   out_6525929466162239676[0] = state[0];
   out_6525929466162239676[1] = state[1];
   out_6525929466162239676[2] = state[2];
   out_6525929466162239676[3] = state[3];
   out_6525929466162239676[4] = state[4];
   out_6525929466162239676[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_6525929466162239676[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_6525929466162239676[7] = state[7];
   out_6525929466162239676[8] = state[8];
}
void F_fun(double *state, double dt, double *out_2819353980597124361) {
   out_2819353980597124361[0] = 1;
   out_2819353980597124361[1] = 0;
   out_2819353980597124361[2] = 0;
   out_2819353980597124361[3] = 0;
   out_2819353980597124361[4] = 0;
   out_2819353980597124361[5] = 0;
   out_2819353980597124361[6] = 0;
   out_2819353980597124361[7] = 0;
   out_2819353980597124361[8] = 0;
   out_2819353980597124361[9] = 0;
   out_2819353980597124361[10] = 1;
   out_2819353980597124361[11] = 0;
   out_2819353980597124361[12] = 0;
   out_2819353980597124361[13] = 0;
   out_2819353980597124361[14] = 0;
   out_2819353980597124361[15] = 0;
   out_2819353980597124361[16] = 0;
   out_2819353980597124361[17] = 0;
   out_2819353980597124361[18] = 0;
   out_2819353980597124361[19] = 0;
   out_2819353980597124361[20] = 1;
   out_2819353980597124361[21] = 0;
   out_2819353980597124361[22] = 0;
   out_2819353980597124361[23] = 0;
   out_2819353980597124361[24] = 0;
   out_2819353980597124361[25] = 0;
   out_2819353980597124361[26] = 0;
   out_2819353980597124361[27] = 0;
   out_2819353980597124361[28] = 0;
   out_2819353980597124361[29] = 0;
   out_2819353980597124361[30] = 1;
   out_2819353980597124361[31] = 0;
   out_2819353980597124361[32] = 0;
   out_2819353980597124361[33] = 0;
   out_2819353980597124361[34] = 0;
   out_2819353980597124361[35] = 0;
   out_2819353980597124361[36] = 0;
   out_2819353980597124361[37] = 0;
   out_2819353980597124361[38] = 0;
   out_2819353980597124361[39] = 0;
   out_2819353980597124361[40] = 1;
   out_2819353980597124361[41] = 0;
   out_2819353980597124361[42] = 0;
   out_2819353980597124361[43] = 0;
   out_2819353980597124361[44] = 0;
   out_2819353980597124361[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_2819353980597124361[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_2819353980597124361[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_2819353980597124361[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_2819353980597124361[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_2819353980597124361[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_2819353980597124361[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_2819353980597124361[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_2819353980597124361[53] = -9.8100000000000005*dt;
   out_2819353980597124361[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_2819353980597124361[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_2819353980597124361[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_2819353980597124361[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_2819353980597124361[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_2819353980597124361[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_2819353980597124361[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_2819353980597124361[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_2819353980597124361[62] = 0;
   out_2819353980597124361[63] = 0;
   out_2819353980597124361[64] = 0;
   out_2819353980597124361[65] = 0;
   out_2819353980597124361[66] = 0;
   out_2819353980597124361[67] = 0;
   out_2819353980597124361[68] = 0;
   out_2819353980597124361[69] = 0;
   out_2819353980597124361[70] = 1;
   out_2819353980597124361[71] = 0;
   out_2819353980597124361[72] = 0;
   out_2819353980597124361[73] = 0;
   out_2819353980597124361[74] = 0;
   out_2819353980597124361[75] = 0;
   out_2819353980597124361[76] = 0;
   out_2819353980597124361[77] = 0;
   out_2819353980597124361[78] = 0;
   out_2819353980597124361[79] = 0;
   out_2819353980597124361[80] = 1;
}
void h_25(double *state, double *unused, double *out_6189447245513617570) {
   out_6189447245513617570[0] = state[6];
}
void H_25(double *state, double *unused, double *out_3234178458103237326) {
   out_3234178458103237326[0] = 0;
   out_3234178458103237326[1] = 0;
   out_3234178458103237326[2] = 0;
   out_3234178458103237326[3] = 0;
   out_3234178458103237326[4] = 0;
   out_3234178458103237326[5] = 0;
   out_3234178458103237326[6] = 1;
   out_3234178458103237326[7] = 0;
   out_3234178458103237326[8] = 0;
}
void h_24(double *state, double *unused, double *out_7649152206074051029) {
   out_7649152206074051029[0] = state[4];
   out_7649152206074051029[1] = state[5];
}
void H_24(double *state, double *unused, double *out_7794173981929387397) {
   out_7794173981929387397[0] = 0;
   out_7794173981929387397[1] = 0;
   out_7794173981929387397[2] = 0;
   out_7794173981929387397[3] = 0;
   out_7794173981929387397[4] = 1;
   out_7794173981929387397[5] = 0;
   out_7794173981929387397[6] = 0;
   out_7794173981929387397[7] = 0;
   out_7794173981929387397[8] = 0;
   out_7794173981929387397[9] = 0;
   out_7794173981929387397[10] = 0;
   out_7794173981929387397[11] = 0;
   out_7794173981929387397[12] = 0;
   out_7794173981929387397[13] = 0;
   out_7794173981929387397[14] = 1;
   out_7794173981929387397[15] = 0;
   out_7794173981929387397[16] = 0;
   out_7794173981929387397[17] = 0;
}
void h_30(double *state, double *unused, double *out_6334967069734272541) {
   out_6334967069734272541[0] = state[4];
}
void H_30(double *state, double *unused, double *out_3104839510959997256) {
   out_3104839510959997256[0] = 0;
   out_3104839510959997256[1] = 0;
   out_3104839510959997256[2] = 0;
   out_3104839510959997256[3] = 0;
   out_3104839510959997256[4] = 1;
   out_3104839510959997256[5] = 0;
   out_3104839510959997256[6] = 0;
   out_3104839510959997256[7] = 0;
   out_3104839510959997256[8] = 0;
}
void h_26(double *state, double *unused, double *out_1333293802073426896) {
   out_1333293802073426896[0] = state[7];
}
void H_26(double *state, double *unused, double *out_507324860770818898) {
   out_507324860770818898[0] = 0;
   out_507324860770818898[1] = 0;
   out_507324860770818898[2] = 0;
   out_507324860770818898[3] = 0;
   out_507324860770818898[4] = 0;
   out_507324860770818898[5] = 0;
   out_507324860770818898[6] = 0;
   out_507324860770818898[7] = 1;
   out_507324860770818898[8] = 0;
}
void h_27(double *state, double *unused, double *out_7255623560535088401) {
   out_7255623560535088401[0] = state[3];
}
void H_27(double *state, double *unused, double *out_930076199159572345) {
   out_930076199159572345[0] = 0;
   out_930076199159572345[1] = 0;
   out_930076199159572345[2] = 0;
   out_930076199159572345[3] = 1;
   out_930076199159572345[4] = 0;
   out_930076199159572345[5] = 0;
   out_930076199159572345[6] = 0;
   out_930076199159572345[7] = 0;
   out_930076199159572345[8] = 0;
}
void h_29(double *state, double *unused, double *out_3730561748925574890) {
   out_3730561748925574890[0] = state[1];
}
void H_29(double *state, double *unused, double *out_3615070855274389440) {
   out_3615070855274389440[0] = 0;
   out_3615070855274389440[1] = 1;
   out_3615070855274389440[2] = 0;
   out_3615070855274389440[3] = 0;
   out_3615070855274389440[4] = 0;
   out_3615070855274389440[5] = 0;
   out_3615070855274389440[6] = 0;
   out_3615070855274389440[7] = 0;
   out_3615070855274389440[8] = 0;
}
void h_28(double *state, double *unused, double *out_2029716344699763454) {
   out_2029716344699763454[0] = state[0];
}
void H_28(double *state, double *unused, double *out_1180343743855347563) {
   out_1180343743855347563[0] = 1;
   out_1180343743855347563[1] = 0;
   out_1180343743855347563[2] = 0;
   out_1180343743855347563[3] = 0;
   out_1180343743855347563[4] = 0;
   out_1180343743855347563[5] = 0;
   out_1180343743855347563[6] = 0;
   out_1180343743855347563[7] = 0;
   out_1180343743855347563[8] = 0;
}
void h_31(double *state, double *unused, double *out_2551997717259595220) {
   out_2551997717259595220[0] = state[8];
}
void H_31(double *state, double *unused, double *out_3264824419980197754) {
   out_3264824419980197754[0] = 0;
   out_3264824419980197754[1] = 0;
   out_3264824419980197754[2] = 0;
   out_3264824419980197754[3] = 0;
   out_3264824419980197754[4] = 0;
   out_3264824419980197754[5] = 0;
   out_3264824419980197754[6] = 0;
   out_3264824419980197754[7] = 0;
   out_3264824419980197754[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_6018065189512211380) {
  err_fun(nom_x, delta_x, out_6018065189512211380);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_1095263434101283480) {
  inv_err_fun(nom_x, true_x, out_1095263434101283480);
}
void car_H_mod_fun(double *state, double *out_2728844015902940614) {
  H_mod_fun(state, out_2728844015902940614);
}
void car_f_fun(double *state, double dt, double *out_6525929466162239676) {
  f_fun(state,  dt, out_6525929466162239676);
}
void car_F_fun(double *state, double dt, double *out_2819353980597124361) {
  F_fun(state,  dt, out_2819353980597124361);
}
void car_h_25(double *state, double *unused, double *out_6189447245513617570) {
  h_25(state, unused, out_6189447245513617570);
}
void car_H_25(double *state, double *unused, double *out_3234178458103237326) {
  H_25(state, unused, out_3234178458103237326);
}
void car_h_24(double *state, double *unused, double *out_7649152206074051029) {
  h_24(state, unused, out_7649152206074051029);
}
void car_H_24(double *state, double *unused, double *out_7794173981929387397) {
  H_24(state, unused, out_7794173981929387397);
}
void car_h_30(double *state, double *unused, double *out_6334967069734272541) {
  h_30(state, unused, out_6334967069734272541);
}
void car_H_30(double *state, double *unused, double *out_3104839510959997256) {
  H_30(state, unused, out_3104839510959997256);
}
void car_h_26(double *state, double *unused, double *out_1333293802073426896) {
  h_26(state, unused, out_1333293802073426896);
}
void car_H_26(double *state, double *unused, double *out_507324860770818898) {
  H_26(state, unused, out_507324860770818898);
}
void car_h_27(double *state, double *unused, double *out_7255623560535088401) {
  h_27(state, unused, out_7255623560535088401);
}
void car_H_27(double *state, double *unused, double *out_930076199159572345) {
  H_27(state, unused, out_930076199159572345);
}
void car_h_29(double *state, double *unused, double *out_3730561748925574890) {
  h_29(state, unused, out_3730561748925574890);
}
void car_H_29(double *state, double *unused, double *out_3615070855274389440) {
  H_29(state, unused, out_3615070855274389440);
}
void car_h_28(double *state, double *unused, double *out_2029716344699763454) {
  h_28(state, unused, out_2029716344699763454);
}
void car_H_28(double *state, double *unused, double *out_1180343743855347563) {
  H_28(state, unused, out_1180343743855347563);
}
void car_h_31(double *state, double *unused, double *out_2551997717259595220) {
  h_31(state, unused, out_2551997717259595220);
}
void car_H_31(double *state, double *unused, double *out_3264824419980197754) {
  H_31(state, unused, out_3264824419980197754);
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
