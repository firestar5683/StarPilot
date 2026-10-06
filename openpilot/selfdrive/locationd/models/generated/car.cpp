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
void err_fun(double *nom_x, double *delta_x, double *out_1207054125356267807) {
   out_1207054125356267807[0] = delta_x[0] + nom_x[0];
   out_1207054125356267807[1] = delta_x[1] + nom_x[1];
   out_1207054125356267807[2] = delta_x[2] + nom_x[2];
   out_1207054125356267807[3] = delta_x[3] + nom_x[3];
   out_1207054125356267807[4] = delta_x[4] + nom_x[4];
   out_1207054125356267807[5] = delta_x[5] + nom_x[5];
   out_1207054125356267807[6] = delta_x[6] + nom_x[6];
   out_1207054125356267807[7] = delta_x[7] + nom_x[7];
   out_1207054125356267807[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_3099046322898442676) {
   out_3099046322898442676[0] = -nom_x[0] + true_x[0];
   out_3099046322898442676[1] = -nom_x[1] + true_x[1];
   out_3099046322898442676[2] = -nom_x[2] + true_x[2];
   out_3099046322898442676[3] = -nom_x[3] + true_x[3];
   out_3099046322898442676[4] = -nom_x[4] + true_x[4];
   out_3099046322898442676[5] = -nom_x[5] + true_x[5];
   out_3099046322898442676[6] = -nom_x[6] + true_x[6];
   out_3099046322898442676[7] = -nom_x[7] + true_x[7];
   out_3099046322898442676[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_8499267737788036021) {
   out_8499267737788036021[0] = 1.0;
   out_8499267737788036021[1] = 0.0;
   out_8499267737788036021[2] = 0.0;
   out_8499267737788036021[3] = 0.0;
   out_8499267737788036021[4] = 0.0;
   out_8499267737788036021[5] = 0.0;
   out_8499267737788036021[6] = 0.0;
   out_8499267737788036021[7] = 0.0;
   out_8499267737788036021[8] = 0.0;
   out_8499267737788036021[9] = 0.0;
   out_8499267737788036021[10] = 1.0;
   out_8499267737788036021[11] = 0.0;
   out_8499267737788036021[12] = 0.0;
   out_8499267737788036021[13] = 0.0;
   out_8499267737788036021[14] = 0.0;
   out_8499267737788036021[15] = 0.0;
   out_8499267737788036021[16] = 0.0;
   out_8499267737788036021[17] = 0.0;
   out_8499267737788036021[18] = 0.0;
   out_8499267737788036021[19] = 0.0;
   out_8499267737788036021[20] = 1.0;
   out_8499267737788036021[21] = 0.0;
   out_8499267737788036021[22] = 0.0;
   out_8499267737788036021[23] = 0.0;
   out_8499267737788036021[24] = 0.0;
   out_8499267737788036021[25] = 0.0;
   out_8499267737788036021[26] = 0.0;
   out_8499267737788036021[27] = 0.0;
   out_8499267737788036021[28] = 0.0;
   out_8499267737788036021[29] = 0.0;
   out_8499267737788036021[30] = 1.0;
   out_8499267737788036021[31] = 0.0;
   out_8499267737788036021[32] = 0.0;
   out_8499267737788036021[33] = 0.0;
   out_8499267737788036021[34] = 0.0;
   out_8499267737788036021[35] = 0.0;
   out_8499267737788036021[36] = 0.0;
   out_8499267737788036021[37] = 0.0;
   out_8499267737788036021[38] = 0.0;
   out_8499267737788036021[39] = 0.0;
   out_8499267737788036021[40] = 1.0;
   out_8499267737788036021[41] = 0.0;
   out_8499267737788036021[42] = 0.0;
   out_8499267737788036021[43] = 0.0;
   out_8499267737788036021[44] = 0.0;
   out_8499267737788036021[45] = 0.0;
   out_8499267737788036021[46] = 0.0;
   out_8499267737788036021[47] = 0.0;
   out_8499267737788036021[48] = 0.0;
   out_8499267737788036021[49] = 0.0;
   out_8499267737788036021[50] = 1.0;
   out_8499267737788036021[51] = 0.0;
   out_8499267737788036021[52] = 0.0;
   out_8499267737788036021[53] = 0.0;
   out_8499267737788036021[54] = 0.0;
   out_8499267737788036021[55] = 0.0;
   out_8499267737788036021[56] = 0.0;
   out_8499267737788036021[57] = 0.0;
   out_8499267737788036021[58] = 0.0;
   out_8499267737788036021[59] = 0.0;
   out_8499267737788036021[60] = 1.0;
   out_8499267737788036021[61] = 0.0;
   out_8499267737788036021[62] = 0.0;
   out_8499267737788036021[63] = 0.0;
   out_8499267737788036021[64] = 0.0;
   out_8499267737788036021[65] = 0.0;
   out_8499267737788036021[66] = 0.0;
   out_8499267737788036021[67] = 0.0;
   out_8499267737788036021[68] = 0.0;
   out_8499267737788036021[69] = 0.0;
   out_8499267737788036021[70] = 1.0;
   out_8499267737788036021[71] = 0.0;
   out_8499267737788036021[72] = 0.0;
   out_8499267737788036021[73] = 0.0;
   out_8499267737788036021[74] = 0.0;
   out_8499267737788036021[75] = 0.0;
   out_8499267737788036021[76] = 0.0;
   out_8499267737788036021[77] = 0.0;
   out_8499267737788036021[78] = 0.0;
   out_8499267737788036021[79] = 0.0;
   out_8499267737788036021[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_8282094013389197429) {
   out_8282094013389197429[0] = state[0];
   out_8282094013389197429[1] = state[1];
   out_8282094013389197429[2] = state[2];
   out_8282094013389197429[3] = state[3];
   out_8282094013389197429[4] = state[4];
   out_8282094013389197429[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_8282094013389197429[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_8282094013389197429[7] = state[7];
   out_8282094013389197429[8] = state[8];
}
void F_fun(double *state, double dt, double *out_2714751254066464584) {
   out_2714751254066464584[0] = 1;
   out_2714751254066464584[1] = 0;
   out_2714751254066464584[2] = 0;
   out_2714751254066464584[3] = 0;
   out_2714751254066464584[4] = 0;
   out_2714751254066464584[5] = 0;
   out_2714751254066464584[6] = 0;
   out_2714751254066464584[7] = 0;
   out_2714751254066464584[8] = 0;
   out_2714751254066464584[9] = 0;
   out_2714751254066464584[10] = 1;
   out_2714751254066464584[11] = 0;
   out_2714751254066464584[12] = 0;
   out_2714751254066464584[13] = 0;
   out_2714751254066464584[14] = 0;
   out_2714751254066464584[15] = 0;
   out_2714751254066464584[16] = 0;
   out_2714751254066464584[17] = 0;
   out_2714751254066464584[18] = 0;
   out_2714751254066464584[19] = 0;
   out_2714751254066464584[20] = 1;
   out_2714751254066464584[21] = 0;
   out_2714751254066464584[22] = 0;
   out_2714751254066464584[23] = 0;
   out_2714751254066464584[24] = 0;
   out_2714751254066464584[25] = 0;
   out_2714751254066464584[26] = 0;
   out_2714751254066464584[27] = 0;
   out_2714751254066464584[28] = 0;
   out_2714751254066464584[29] = 0;
   out_2714751254066464584[30] = 1;
   out_2714751254066464584[31] = 0;
   out_2714751254066464584[32] = 0;
   out_2714751254066464584[33] = 0;
   out_2714751254066464584[34] = 0;
   out_2714751254066464584[35] = 0;
   out_2714751254066464584[36] = 0;
   out_2714751254066464584[37] = 0;
   out_2714751254066464584[38] = 0;
   out_2714751254066464584[39] = 0;
   out_2714751254066464584[40] = 1;
   out_2714751254066464584[41] = 0;
   out_2714751254066464584[42] = 0;
   out_2714751254066464584[43] = 0;
   out_2714751254066464584[44] = 0;
   out_2714751254066464584[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_2714751254066464584[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_2714751254066464584[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_2714751254066464584[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_2714751254066464584[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_2714751254066464584[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_2714751254066464584[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_2714751254066464584[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_2714751254066464584[53] = -9.8100000000000005*dt;
   out_2714751254066464584[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_2714751254066464584[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_2714751254066464584[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_2714751254066464584[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_2714751254066464584[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_2714751254066464584[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_2714751254066464584[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_2714751254066464584[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_2714751254066464584[62] = 0;
   out_2714751254066464584[63] = 0;
   out_2714751254066464584[64] = 0;
   out_2714751254066464584[65] = 0;
   out_2714751254066464584[66] = 0;
   out_2714751254066464584[67] = 0;
   out_2714751254066464584[68] = 0;
   out_2714751254066464584[69] = 0;
   out_2714751254066464584[70] = 1;
   out_2714751254066464584[71] = 0;
   out_2714751254066464584[72] = 0;
   out_2714751254066464584[73] = 0;
   out_2714751254066464584[74] = 0;
   out_2714751254066464584[75] = 0;
   out_2714751254066464584[76] = 0;
   out_2714751254066464584[77] = 0;
   out_2714751254066464584[78] = 0;
   out_2714751254066464584[79] = 0;
   out_2714751254066464584[80] = 1;
}
void h_25(double *state, double *unused, double *out_9062879424533513701) {
   out_9062879424533513701[0] = state[6];
}
void H_25(double *state, double *unused, double *out_6424495685932023918) {
   out_6424495685932023918[0] = 0;
   out_6424495685932023918[1] = 0;
   out_6424495685932023918[2] = 0;
   out_6424495685932023918[3] = 0;
   out_6424495685932023918[4] = 0;
   out_6424495685932023918[5] = 0;
   out_6424495685932023918[6] = 1;
   out_6424495685932023918[7] = 0;
   out_6424495685932023918[8] = 0;
}
void h_24(double *state, double *unused, double *out_2252532558771607279) {
   out_2252532558771607279[0] = state[4];
   out_2252532558771607279[1] = state[5];
}
void H_24(double *state, double *unused, double *out_2866570087129700782) {
   out_2866570087129700782[0] = 0;
   out_2866570087129700782[1] = 0;
   out_2866570087129700782[2] = 0;
   out_2866570087129700782[3] = 0;
   out_2866570087129700782[4] = 1;
   out_2866570087129700782[5] = 0;
   out_2866570087129700782[6] = 0;
   out_2866570087129700782[7] = 0;
   out_2866570087129700782[8] = 0;
   out_2866570087129700782[9] = 0;
   out_2866570087129700782[10] = 0;
   out_2866570087129700782[11] = 0;
   out_2866570087129700782[12] = 0;
   out_2866570087129700782[13] = 0;
   out_2866570087129700782[14] = 1;
   out_2866570087129700782[15] = 0;
   out_2866570087129700782[16] = 0;
   out_2866570087129700782[17] = 0;
}
void h_30(double *state, double *unused, double *out_4624883595742397937) {
   out_4624883595742397937[0] = state[4];
}
void H_30(double *state, double *unused, double *out_3906162727424775291) {
   out_3906162727424775291[0] = 0;
   out_3906162727424775291[1] = 0;
   out_3906162727424775291[2] = 0;
   out_3906162727424775291[3] = 0;
   out_3906162727424775291[4] = 1;
   out_3906162727424775291[5] = 0;
   out_3906162727424775291[6] = 0;
   out_3906162727424775291[7] = 0;
   out_3906162727424775291[8] = 0;
}
void h_26(double *state, double *unused, double *out_3556539275727349414) {
   out_3556539275727349414[0] = state[7];
}
void H_26(double *state, double *unused, double *out_8280745068903471474) {
   out_8280745068903471474[0] = 0;
   out_8280745068903471474[1] = 0;
   out_8280745068903471474[2] = 0;
   out_8280745068903471474[3] = 0;
   out_8280745068903471474[4] = 0;
   out_8280745068903471474[5] = 0;
   out_8280745068903471474[6] = 0;
   out_8280745068903471474[7] = 1;
   out_8280745068903471474[8] = 0;
}
void h_27(double *state, double *unused, double *out_6779459328367340264) {
   out_6779459328367340264[0] = state[3];
}
void H_27(double *state, double *unused, double *out_1682568656240832074) {
   out_1682568656240832074[0] = 0;
   out_1682568656240832074[1] = 0;
   out_1682568656240832074[2] = 0;
   out_1682568656240832074[3] = 1;
   out_1682568656240832074[4] = 0;
   out_1682568656240832074[5] = 0;
   out_1682568656240832074[6] = 0;
   out_1682568656240832074[7] = 0;
   out_1682568656240832074[8] = 0;
}
void h_29(double *state, double *unused, double *out_423756628618645706) {
   out_423756628618645706[0] = state[1];
}
void H_29(double *state, double *unused, double *out_3395931383110383107) {
   out_3395931383110383107[0] = 0;
   out_3395931383110383107[1] = 1;
   out_3395931383110383107[2] = 0;
   out_3395931383110383107[3] = 0;
   out_3395931383110383107[4] = 0;
   out_3395931383110383107[5] = 0;
   out_3395931383110383107[6] = 0;
   out_3395931383110383107[7] = 0;
   out_3395931383110383107[8] = 0;
}
void h_28(double *state, double *unused, double *out_7382775213043817781) {
   out_7382775213043817781[0] = state[0];
}
void H_28(double *state, double *unused, double *out_8478330400179913681) {
   out_8478330400179913681[0] = 1;
   out_8478330400179913681[1] = 0;
   out_8478330400179913681[2] = 0;
   out_8478330400179913681[3] = 0;
   out_8478330400179913681[4] = 0;
   out_8478330400179913681[5] = 0;
   out_8478330400179913681[6] = 0;
   out_8478330400179913681[7] = 0;
   out_8478330400179913681[8] = 0;
}
void h_31(double *state, double *unused, double *out_8905692756182384556) {
   out_8905692756182384556[0] = state[8];
}
void H_31(double *state, double *unused, double *out_6393849724055063490) {
   out_6393849724055063490[0] = 0;
   out_6393849724055063490[1] = 0;
   out_6393849724055063490[2] = 0;
   out_6393849724055063490[3] = 0;
   out_6393849724055063490[4] = 0;
   out_6393849724055063490[5] = 0;
   out_6393849724055063490[6] = 0;
   out_6393849724055063490[7] = 0;
   out_6393849724055063490[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_1207054125356267807) {
  err_fun(nom_x, delta_x, out_1207054125356267807);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_3099046322898442676) {
  inv_err_fun(nom_x, true_x, out_3099046322898442676);
}
void car_H_mod_fun(double *state, double *out_8499267737788036021) {
  H_mod_fun(state, out_8499267737788036021);
}
void car_f_fun(double *state, double dt, double *out_8282094013389197429) {
  f_fun(state,  dt, out_8282094013389197429);
}
void car_F_fun(double *state, double dt, double *out_2714751254066464584) {
  F_fun(state,  dt, out_2714751254066464584);
}
void car_h_25(double *state, double *unused, double *out_9062879424533513701) {
  h_25(state, unused, out_9062879424533513701);
}
void car_H_25(double *state, double *unused, double *out_6424495685932023918) {
  H_25(state, unused, out_6424495685932023918);
}
void car_h_24(double *state, double *unused, double *out_2252532558771607279) {
  h_24(state, unused, out_2252532558771607279);
}
void car_H_24(double *state, double *unused, double *out_2866570087129700782) {
  H_24(state, unused, out_2866570087129700782);
}
void car_h_30(double *state, double *unused, double *out_4624883595742397937) {
  h_30(state, unused, out_4624883595742397937);
}
void car_H_30(double *state, double *unused, double *out_3906162727424775291) {
  H_30(state, unused, out_3906162727424775291);
}
void car_h_26(double *state, double *unused, double *out_3556539275727349414) {
  h_26(state, unused, out_3556539275727349414);
}
void car_H_26(double *state, double *unused, double *out_8280745068903471474) {
  H_26(state, unused, out_8280745068903471474);
}
void car_h_27(double *state, double *unused, double *out_6779459328367340264) {
  h_27(state, unused, out_6779459328367340264);
}
void car_H_27(double *state, double *unused, double *out_1682568656240832074) {
  H_27(state, unused, out_1682568656240832074);
}
void car_h_29(double *state, double *unused, double *out_423756628618645706) {
  h_29(state, unused, out_423756628618645706);
}
void car_H_29(double *state, double *unused, double *out_3395931383110383107) {
  H_29(state, unused, out_3395931383110383107);
}
void car_h_28(double *state, double *unused, double *out_7382775213043817781) {
  h_28(state, unused, out_7382775213043817781);
}
void car_H_28(double *state, double *unused, double *out_8478330400179913681) {
  H_28(state, unused, out_8478330400179913681);
}
void car_h_31(double *state, double *unused, double *out_8905692756182384556) {
  h_31(state, unused, out_8905692756182384556);
}
void car_H_31(double *state, double *unused, double *out_6393849724055063490) {
  H_31(state, unused, out_6393849724055063490);
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
