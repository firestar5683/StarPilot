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
void err_fun(double *nom_x, double *delta_x, double *out_5063363100648596688) {
   out_5063363100648596688[0] = delta_x[0] + nom_x[0];
   out_5063363100648596688[1] = delta_x[1] + nom_x[1];
   out_5063363100648596688[2] = delta_x[2] + nom_x[2];
   out_5063363100648596688[3] = delta_x[3] + nom_x[3];
   out_5063363100648596688[4] = delta_x[4] + nom_x[4];
   out_5063363100648596688[5] = delta_x[5] + nom_x[5];
   out_5063363100648596688[6] = delta_x[6] + nom_x[6];
   out_5063363100648596688[7] = delta_x[7] + nom_x[7];
   out_5063363100648596688[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_1051973791362877167) {
   out_1051973791362877167[0] = -nom_x[0] + true_x[0];
   out_1051973791362877167[1] = -nom_x[1] + true_x[1];
   out_1051973791362877167[2] = -nom_x[2] + true_x[2];
   out_1051973791362877167[3] = -nom_x[3] + true_x[3];
   out_1051973791362877167[4] = -nom_x[4] + true_x[4];
   out_1051973791362877167[5] = -nom_x[5] + true_x[5];
   out_1051973791362877167[6] = -nom_x[6] + true_x[6];
   out_1051973791362877167[7] = -nom_x[7] + true_x[7];
   out_1051973791362877167[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_5315869906856267240) {
   out_5315869906856267240[0] = 1.0;
   out_5315869906856267240[1] = 0.0;
   out_5315869906856267240[2] = 0.0;
   out_5315869906856267240[3] = 0.0;
   out_5315869906856267240[4] = 0.0;
   out_5315869906856267240[5] = 0.0;
   out_5315869906856267240[6] = 0.0;
   out_5315869906856267240[7] = 0.0;
   out_5315869906856267240[8] = 0.0;
   out_5315869906856267240[9] = 0.0;
   out_5315869906856267240[10] = 1.0;
   out_5315869906856267240[11] = 0.0;
   out_5315869906856267240[12] = 0.0;
   out_5315869906856267240[13] = 0.0;
   out_5315869906856267240[14] = 0.0;
   out_5315869906856267240[15] = 0.0;
   out_5315869906856267240[16] = 0.0;
   out_5315869906856267240[17] = 0.0;
   out_5315869906856267240[18] = 0.0;
   out_5315869906856267240[19] = 0.0;
   out_5315869906856267240[20] = 1.0;
   out_5315869906856267240[21] = 0.0;
   out_5315869906856267240[22] = 0.0;
   out_5315869906856267240[23] = 0.0;
   out_5315869906856267240[24] = 0.0;
   out_5315869906856267240[25] = 0.0;
   out_5315869906856267240[26] = 0.0;
   out_5315869906856267240[27] = 0.0;
   out_5315869906856267240[28] = 0.0;
   out_5315869906856267240[29] = 0.0;
   out_5315869906856267240[30] = 1.0;
   out_5315869906856267240[31] = 0.0;
   out_5315869906856267240[32] = 0.0;
   out_5315869906856267240[33] = 0.0;
   out_5315869906856267240[34] = 0.0;
   out_5315869906856267240[35] = 0.0;
   out_5315869906856267240[36] = 0.0;
   out_5315869906856267240[37] = 0.0;
   out_5315869906856267240[38] = 0.0;
   out_5315869906856267240[39] = 0.0;
   out_5315869906856267240[40] = 1.0;
   out_5315869906856267240[41] = 0.0;
   out_5315869906856267240[42] = 0.0;
   out_5315869906856267240[43] = 0.0;
   out_5315869906856267240[44] = 0.0;
   out_5315869906856267240[45] = 0.0;
   out_5315869906856267240[46] = 0.0;
   out_5315869906856267240[47] = 0.0;
   out_5315869906856267240[48] = 0.0;
   out_5315869906856267240[49] = 0.0;
   out_5315869906856267240[50] = 1.0;
   out_5315869906856267240[51] = 0.0;
   out_5315869906856267240[52] = 0.0;
   out_5315869906856267240[53] = 0.0;
   out_5315869906856267240[54] = 0.0;
   out_5315869906856267240[55] = 0.0;
   out_5315869906856267240[56] = 0.0;
   out_5315869906856267240[57] = 0.0;
   out_5315869906856267240[58] = 0.0;
   out_5315869906856267240[59] = 0.0;
   out_5315869906856267240[60] = 1.0;
   out_5315869906856267240[61] = 0.0;
   out_5315869906856267240[62] = 0.0;
   out_5315869906856267240[63] = 0.0;
   out_5315869906856267240[64] = 0.0;
   out_5315869906856267240[65] = 0.0;
   out_5315869906856267240[66] = 0.0;
   out_5315869906856267240[67] = 0.0;
   out_5315869906856267240[68] = 0.0;
   out_5315869906856267240[69] = 0.0;
   out_5315869906856267240[70] = 1.0;
   out_5315869906856267240[71] = 0.0;
   out_5315869906856267240[72] = 0.0;
   out_5315869906856267240[73] = 0.0;
   out_5315869906856267240[74] = 0.0;
   out_5315869906856267240[75] = 0.0;
   out_5315869906856267240[76] = 0.0;
   out_5315869906856267240[77] = 0.0;
   out_5315869906856267240[78] = 0.0;
   out_5315869906856267240[79] = 0.0;
   out_5315869906856267240[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_2679807483918754558) {
   out_2679807483918754558[0] = state[0];
   out_2679807483918754558[1] = state[1];
   out_2679807483918754558[2] = state[2];
   out_2679807483918754558[3] = state[3];
   out_2679807483918754558[4] = state[4];
   out_2679807483918754558[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_2679807483918754558[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_2679807483918754558[7] = state[7];
   out_2679807483918754558[8] = state[8];
}
void F_fun(double *state, double dt, double *out_8053926087528305413) {
   out_8053926087528305413[0] = 1;
   out_8053926087528305413[1] = 0;
   out_8053926087528305413[2] = 0;
   out_8053926087528305413[3] = 0;
   out_8053926087528305413[4] = 0;
   out_8053926087528305413[5] = 0;
   out_8053926087528305413[6] = 0;
   out_8053926087528305413[7] = 0;
   out_8053926087528305413[8] = 0;
   out_8053926087528305413[9] = 0;
   out_8053926087528305413[10] = 1;
   out_8053926087528305413[11] = 0;
   out_8053926087528305413[12] = 0;
   out_8053926087528305413[13] = 0;
   out_8053926087528305413[14] = 0;
   out_8053926087528305413[15] = 0;
   out_8053926087528305413[16] = 0;
   out_8053926087528305413[17] = 0;
   out_8053926087528305413[18] = 0;
   out_8053926087528305413[19] = 0;
   out_8053926087528305413[20] = 1;
   out_8053926087528305413[21] = 0;
   out_8053926087528305413[22] = 0;
   out_8053926087528305413[23] = 0;
   out_8053926087528305413[24] = 0;
   out_8053926087528305413[25] = 0;
   out_8053926087528305413[26] = 0;
   out_8053926087528305413[27] = 0;
   out_8053926087528305413[28] = 0;
   out_8053926087528305413[29] = 0;
   out_8053926087528305413[30] = 1;
   out_8053926087528305413[31] = 0;
   out_8053926087528305413[32] = 0;
   out_8053926087528305413[33] = 0;
   out_8053926087528305413[34] = 0;
   out_8053926087528305413[35] = 0;
   out_8053926087528305413[36] = 0;
   out_8053926087528305413[37] = 0;
   out_8053926087528305413[38] = 0;
   out_8053926087528305413[39] = 0;
   out_8053926087528305413[40] = 1;
   out_8053926087528305413[41] = 0;
   out_8053926087528305413[42] = 0;
   out_8053926087528305413[43] = 0;
   out_8053926087528305413[44] = 0;
   out_8053926087528305413[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_8053926087528305413[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_8053926087528305413[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_8053926087528305413[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_8053926087528305413[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_8053926087528305413[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_8053926087528305413[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_8053926087528305413[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_8053926087528305413[53] = -9.8100000000000005*dt;
   out_8053926087528305413[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_8053926087528305413[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_8053926087528305413[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_8053926087528305413[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_8053926087528305413[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_8053926087528305413[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_8053926087528305413[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_8053926087528305413[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_8053926087528305413[62] = 0;
   out_8053926087528305413[63] = 0;
   out_8053926087528305413[64] = 0;
   out_8053926087528305413[65] = 0;
   out_8053926087528305413[66] = 0;
   out_8053926087528305413[67] = 0;
   out_8053926087528305413[68] = 0;
   out_8053926087528305413[69] = 0;
   out_8053926087528305413[70] = 1;
   out_8053926087528305413[71] = 0;
   out_8053926087528305413[72] = 0;
   out_8053926087528305413[73] = 0;
   out_8053926087528305413[74] = 0;
   out_8053926087528305413[75] = 0;
   out_8053926087528305413[76] = 0;
   out_8053926087528305413[77] = 0;
   out_8053926087528305413[78] = 0;
   out_8053926087528305413[79] = 0;
   out_8053926087528305413[80] = 1;
}
void h_25(double *state, double *unused, double *out_5716369086896639497) {
   out_5716369086896639497[0] = state[6];
}
void H_25(double *state, double *unused, double *out_3877318319055969997) {
   out_3877318319055969997[0] = 0;
   out_3877318319055969997[1] = 0;
   out_3877318319055969997[2] = 0;
   out_3877318319055969997[3] = 0;
   out_3877318319055969997[4] = 0;
   out_3877318319055969997[5] = 0;
   out_3877318319055969997[6] = 1;
   out_3877318319055969997[7] = 0;
   out_3877318319055969997[8] = 0;
}
void h_24(double *state, double *unused, double *out_8949486097258288203) {
   out_8949486097258288203[0] = state[4];
   out_8949486097258288203[1] = state[5];
}
void H_24(double *state, double *unused, double *out_6049967918061469563) {
   out_6049967918061469563[0] = 0;
   out_6049967918061469563[1] = 0;
   out_6049967918061469563[2] = 0;
   out_6049967918061469563[3] = 0;
   out_6049967918061469563[4] = 1;
   out_6049967918061469563[5] = 0;
   out_6049967918061469563[6] = 0;
   out_6049967918061469563[7] = 0;
   out_6049967918061469563[8] = 0;
   out_6049967918061469563[9] = 0;
   out_6049967918061469563[10] = 0;
   out_6049967918061469563[11] = 0;
   out_6049967918061469563[12] = 0;
   out_6049967918061469563[13] = 0;
   out_6049967918061469563[14] = 1;
   out_6049967918061469563[15] = 0;
   out_6049967918061469563[16] = 0;
   out_6049967918061469563[17] = 0;
}
void h_30(double *state, double *unused, double *out_5873555755247768642) {
   out_5873555755247768642[0] = state[4];
}
void H_30(double *state, double *unused, double *out_3039372022435646758) {
   out_3039372022435646758[0] = 0;
   out_3039372022435646758[1] = 0;
   out_3039372022435646758[2] = 0;
   out_3039372022435646758[3] = 0;
   out_3039372022435646758[4] = 1;
   out_3039372022435646758[5] = 0;
   out_3039372022435646758[6] = 0;
   out_3039372022435646758[7] = 0;
   out_3039372022435646758[8] = 0;
}
void h_26(double *state, double *unused, double *out_8147827403163551441) {
   out_8147827403163551441[0] = state[7];
}
void H_26(double *state, double *unused, double *out_7618821637930026221) {
   out_7618821637930026221[0] = 0;
   out_7618821637930026221[1] = 0;
   out_7618821637930026221[2] = 0;
   out_7618821637930026221[3] = 0;
   out_7618821637930026221[4] = 0;
   out_7618821637930026221[5] = 0;
   out_7618821637930026221[6] = 0;
   out_7618821637930026221[7] = 1;
   out_7618821637930026221[8] = 0;
}
void h_27(double *state, double *unused, double *out_3868275412420834157) {
   out_3868275412420834157[0] = state[3];
}
void H_27(double *state, double *unused, double *out_864608710635221847) {
   out_864608710635221847[0] = 0;
   out_864608710635221847[1] = 0;
   out_864608710635221847[2] = 0;
   out_864608710635221847[3] = 1;
   out_864608710635221847[4] = 0;
   out_864608710635221847[5] = 0;
   out_864608710635221847[6] = 0;
   out_864608710635221847[7] = 0;
   out_864608710635221847[8] = 0;
}
void h_29(double *state, double *unused, double *out_2922753709018228498) {
   out_2922753709018228498[0] = state[1];
}
void H_29(double *state, double *unused, double *out_3549603366750038942) {
   out_3549603366750038942[0] = 0;
   out_3549603366750038942[1] = 1;
   out_3549603366750038942[2] = 0;
   out_3549603366750038942[3] = 0;
   out_3549603366750038942[4] = 0;
   out_3549603366750038942[5] = 0;
   out_3549603366750038942[6] = 0;
   out_3549603366750038942[7] = 0;
   out_3549603366750038942[8] = 0;
}
void h_28(double *state, double *unused, double *out_2837524384607109846) {
   out_2837524384607109846[0] = state[0];
}
void H_28(double *state, double *unused, double *out_5931153033303859760) {
   out_5931153033303859760[0] = 1;
   out_5931153033303859760[1] = 0;
   out_5931153033303859760[2] = 0;
   out_5931153033303859760[3] = 0;
   out_5931153033303859760[4] = 0;
   out_5931153033303859760[5] = 0;
   out_5931153033303859760[6] = 0;
   out_5931153033303859760[7] = 0;
   out_5931153033303859760[8] = 0;
}
void h_31(double *state, double *unused, double *out_7419317287452796635) {
   out_7419317287452796635[0] = state[8];
}
void H_31(double *state, double *unused, double *out_3846672357179009569) {
   out_3846672357179009569[0] = 0;
   out_3846672357179009569[1] = 0;
   out_3846672357179009569[2] = 0;
   out_3846672357179009569[3] = 0;
   out_3846672357179009569[4] = 0;
   out_3846672357179009569[5] = 0;
   out_3846672357179009569[6] = 0;
   out_3846672357179009569[7] = 0;
   out_3846672357179009569[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_5063363100648596688) {
  err_fun(nom_x, delta_x, out_5063363100648596688);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_1051973791362877167) {
  inv_err_fun(nom_x, true_x, out_1051973791362877167);
}
void car_H_mod_fun(double *state, double *out_5315869906856267240) {
  H_mod_fun(state, out_5315869906856267240);
}
void car_f_fun(double *state, double dt, double *out_2679807483918754558) {
  f_fun(state,  dt, out_2679807483918754558);
}
void car_F_fun(double *state, double dt, double *out_8053926087528305413) {
  F_fun(state,  dt, out_8053926087528305413);
}
void car_h_25(double *state, double *unused, double *out_5716369086896639497) {
  h_25(state, unused, out_5716369086896639497);
}
void car_H_25(double *state, double *unused, double *out_3877318319055969997) {
  H_25(state, unused, out_3877318319055969997);
}
void car_h_24(double *state, double *unused, double *out_8949486097258288203) {
  h_24(state, unused, out_8949486097258288203);
}
void car_H_24(double *state, double *unused, double *out_6049967918061469563) {
  H_24(state, unused, out_6049967918061469563);
}
void car_h_30(double *state, double *unused, double *out_5873555755247768642) {
  h_30(state, unused, out_5873555755247768642);
}
void car_H_30(double *state, double *unused, double *out_3039372022435646758) {
  H_30(state, unused, out_3039372022435646758);
}
void car_h_26(double *state, double *unused, double *out_8147827403163551441) {
  h_26(state, unused, out_8147827403163551441);
}
void car_H_26(double *state, double *unused, double *out_7618821637930026221) {
  H_26(state, unused, out_7618821637930026221);
}
void car_h_27(double *state, double *unused, double *out_3868275412420834157) {
  h_27(state, unused, out_3868275412420834157);
}
void car_H_27(double *state, double *unused, double *out_864608710635221847) {
  H_27(state, unused, out_864608710635221847);
}
void car_h_29(double *state, double *unused, double *out_2922753709018228498) {
  h_29(state, unused, out_2922753709018228498);
}
void car_H_29(double *state, double *unused, double *out_3549603366750038942) {
  H_29(state, unused, out_3549603366750038942);
}
void car_h_28(double *state, double *unused, double *out_2837524384607109846) {
  h_28(state, unused, out_2837524384607109846);
}
void car_H_28(double *state, double *unused, double *out_5931153033303859760) {
  H_28(state, unused, out_5931153033303859760);
}
void car_h_31(double *state, double *unused, double *out_7419317287452796635) {
  h_31(state, unused, out_7419317287452796635);
}
void car_H_31(double *state, double *unused, double *out_3846672357179009569) {
  H_31(state, unused, out_3846672357179009569);
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
