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
void err_fun(double *nom_x, double *delta_x, double *out_7751375231448978305) {
   out_7751375231448978305[0] = delta_x[0] + nom_x[0];
   out_7751375231448978305[1] = delta_x[1] + nom_x[1];
   out_7751375231448978305[2] = delta_x[2] + nom_x[2];
   out_7751375231448978305[3] = delta_x[3] + nom_x[3];
   out_7751375231448978305[4] = delta_x[4] + nom_x[4];
   out_7751375231448978305[5] = delta_x[5] + nom_x[5];
   out_7751375231448978305[6] = delta_x[6] + nom_x[6];
   out_7751375231448978305[7] = delta_x[7] + nom_x[7];
   out_7751375231448978305[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_1186045100449225538) {
   out_1186045100449225538[0] = -nom_x[0] + true_x[0];
   out_1186045100449225538[1] = -nom_x[1] + true_x[1];
   out_1186045100449225538[2] = -nom_x[2] + true_x[2];
   out_1186045100449225538[3] = -nom_x[3] + true_x[3];
   out_1186045100449225538[4] = -nom_x[4] + true_x[4];
   out_1186045100449225538[5] = -nom_x[5] + true_x[5];
   out_1186045100449225538[6] = -nom_x[6] + true_x[6];
   out_1186045100449225538[7] = -nom_x[7] + true_x[7];
   out_1186045100449225538[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_5403210608595880924) {
   out_5403210608595880924[0] = 1.0;
   out_5403210608595880924[1] = 0.0;
   out_5403210608595880924[2] = 0.0;
   out_5403210608595880924[3] = 0.0;
   out_5403210608595880924[4] = 0.0;
   out_5403210608595880924[5] = 0.0;
   out_5403210608595880924[6] = 0.0;
   out_5403210608595880924[7] = 0.0;
   out_5403210608595880924[8] = 0.0;
   out_5403210608595880924[9] = 0.0;
   out_5403210608595880924[10] = 1.0;
   out_5403210608595880924[11] = 0.0;
   out_5403210608595880924[12] = 0.0;
   out_5403210608595880924[13] = 0.0;
   out_5403210608595880924[14] = 0.0;
   out_5403210608595880924[15] = 0.0;
   out_5403210608595880924[16] = 0.0;
   out_5403210608595880924[17] = 0.0;
   out_5403210608595880924[18] = 0.0;
   out_5403210608595880924[19] = 0.0;
   out_5403210608595880924[20] = 1.0;
   out_5403210608595880924[21] = 0.0;
   out_5403210608595880924[22] = 0.0;
   out_5403210608595880924[23] = 0.0;
   out_5403210608595880924[24] = 0.0;
   out_5403210608595880924[25] = 0.0;
   out_5403210608595880924[26] = 0.0;
   out_5403210608595880924[27] = 0.0;
   out_5403210608595880924[28] = 0.0;
   out_5403210608595880924[29] = 0.0;
   out_5403210608595880924[30] = 1.0;
   out_5403210608595880924[31] = 0.0;
   out_5403210608595880924[32] = 0.0;
   out_5403210608595880924[33] = 0.0;
   out_5403210608595880924[34] = 0.0;
   out_5403210608595880924[35] = 0.0;
   out_5403210608595880924[36] = 0.0;
   out_5403210608595880924[37] = 0.0;
   out_5403210608595880924[38] = 0.0;
   out_5403210608595880924[39] = 0.0;
   out_5403210608595880924[40] = 1.0;
   out_5403210608595880924[41] = 0.0;
   out_5403210608595880924[42] = 0.0;
   out_5403210608595880924[43] = 0.0;
   out_5403210608595880924[44] = 0.0;
   out_5403210608595880924[45] = 0.0;
   out_5403210608595880924[46] = 0.0;
   out_5403210608595880924[47] = 0.0;
   out_5403210608595880924[48] = 0.0;
   out_5403210608595880924[49] = 0.0;
   out_5403210608595880924[50] = 1.0;
   out_5403210608595880924[51] = 0.0;
   out_5403210608595880924[52] = 0.0;
   out_5403210608595880924[53] = 0.0;
   out_5403210608595880924[54] = 0.0;
   out_5403210608595880924[55] = 0.0;
   out_5403210608595880924[56] = 0.0;
   out_5403210608595880924[57] = 0.0;
   out_5403210608595880924[58] = 0.0;
   out_5403210608595880924[59] = 0.0;
   out_5403210608595880924[60] = 1.0;
   out_5403210608595880924[61] = 0.0;
   out_5403210608595880924[62] = 0.0;
   out_5403210608595880924[63] = 0.0;
   out_5403210608595880924[64] = 0.0;
   out_5403210608595880924[65] = 0.0;
   out_5403210608595880924[66] = 0.0;
   out_5403210608595880924[67] = 0.0;
   out_5403210608595880924[68] = 0.0;
   out_5403210608595880924[69] = 0.0;
   out_5403210608595880924[70] = 1.0;
   out_5403210608595880924[71] = 0.0;
   out_5403210608595880924[72] = 0.0;
   out_5403210608595880924[73] = 0.0;
   out_5403210608595880924[74] = 0.0;
   out_5403210608595880924[75] = 0.0;
   out_5403210608595880924[76] = 0.0;
   out_5403210608595880924[77] = 0.0;
   out_5403210608595880924[78] = 0.0;
   out_5403210608595880924[79] = 0.0;
   out_5403210608595880924[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_3846473641327680019) {
   out_3846473641327680019[0] = state[0];
   out_3846473641327680019[1] = state[1];
   out_3846473641327680019[2] = state[2];
   out_3846473641327680019[3] = state[3];
   out_3846473641327680019[4] = state[4];
   out_3846473641327680019[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_3846473641327680019[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_3846473641327680019[7] = state[7];
   out_3846473641327680019[8] = state[8];
}
void F_fun(double *state, double dt, double *out_6505574540477860652) {
   out_6505574540477860652[0] = 1;
   out_6505574540477860652[1] = 0;
   out_6505574540477860652[2] = 0;
   out_6505574540477860652[3] = 0;
   out_6505574540477860652[4] = 0;
   out_6505574540477860652[5] = 0;
   out_6505574540477860652[6] = 0;
   out_6505574540477860652[7] = 0;
   out_6505574540477860652[8] = 0;
   out_6505574540477860652[9] = 0;
   out_6505574540477860652[10] = 1;
   out_6505574540477860652[11] = 0;
   out_6505574540477860652[12] = 0;
   out_6505574540477860652[13] = 0;
   out_6505574540477860652[14] = 0;
   out_6505574540477860652[15] = 0;
   out_6505574540477860652[16] = 0;
   out_6505574540477860652[17] = 0;
   out_6505574540477860652[18] = 0;
   out_6505574540477860652[19] = 0;
   out_6505574540477860652[20] = 1;
   out_6505574540477860652[21] = 0;
   out_6505574540477860652[22] = 0;
   out_6505574540477860652[23] = 0;
   out_6505574540477860652[24] = 0;
   out_6505574540477860652[25] = 0;
   out_6505574540477860652[26] = 0;
   out_6505574540477860652[27] = 0;
   out_6505574540477860652[28] = 0;
   out_6505574540477860652[29] = 0;
   out_6505574540477860652[30] = 1;
   out_6505574540477860652[31] = 0;
   out_6505574540477860652[32] = 0;
   out_6505574540477860652[33] = 0;
   out_6505574540477860652[34] = 0;
   out_6505574540477860652[35] = 0;
   out_6505574540477860652[36] = 0;
   out_6505574540477860652[37] = 0;
   out_6505574540477860652[38] = 0;
   out_6505574540477860652[39] = 0;
   out_6505574540477860652[40] = 1;
   out_6505574540477860652[41] = 0;
   out_6505574540477860652[42] = 0;
   out_6505574540477860652[43] = 0;
   out_6505574540477860652[44] = 0;
   out_6505574540477860652[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_6505574540477860652[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_6505574540477860652[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_6505574540477860652[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_6505574540477860652[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_6505574540477860652[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_6505574540477860652[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_6505574540477860652[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_6505574540477860652[53] = -9.8100000000000005*dt;
   out_6505574540477860652[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_6505574540477860652[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_6505574540477860652[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_6505574540477860652[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_6505574540477860652[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_6505574540477860652[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_6505574540477860652[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_6505574540477860652[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_6505574540477860652[62] = 0;
   out_6505574540477860652[63] = 0;
   out_6505574540477860652[64] = 0;
   out_6505574540477860652[65] = 0;
   out_6505574540477860652[66] = 0;
   out_6505574540477860652[67] = 0;
   out_6505574540477860652[68] = 0;
   out_6505574540477860652[69] = 0;
   out_6505574540477860652[70] = 1;
   out_6505574540477860652[71] = 0;
   out_6505574540477860652[72] = 0;
   out_6505574540477860652[73] = 0;
   out_6505574540477860652[74] = 0;
   out_6505574540477860652[75] = 0;
   out_6505574540477860652[76] = 0;
   out_6505574540477860652[77] = 0;
   out_6505574540477860652[78] = 0;
   out_6505574540477860652[79] = 0;
   out_6505574540477860652[80] = 1;
}
void h_25(double *state, double *unused, double *out_1325906349074366668) {
   out_1325906349074366668[0] = state[6];
}
void H_25(double *state, double *unused, double *out_693697758010493692) {
   out_693697758010493692[0] = 0;
   out_693697758010493692[1] = 0;
   out_693697758010493692[2] = 0;
   out_693697758010493692[3] = 0;
   out_693697758010493692[4] = 0;
   out_693697758010493692[5] = 0;
   out_693697758010493692[6] = 1;
   out_693697758010493692[7] = 0;
   out_693697758010493692[8] = 0;
}
void h_24(double *state, double *unused, double *out_7507130987037302702) {
   out_7507130987037302702[0] = state[4];
   out_7507130987037302702[1] = state[5];
}
void H_24(double *state, double *unused, double *out_2864227840791829444) {
   out_2864227840791829444[0] = 0;
   out_2864227840791829444[1] = 0;
   out_2864227840791829444[2] = 0;
   out_2864227840791829444[3] = 0;
   out_2864227840791829444[4] = 1;
   out_2864227840791829444[5] = 0;
   out_2864227840791829444[6] = 0;
   out_2864227840791829444[7] = 0;
   out_2864227840791829444[8] = 0;
   out_2864227840791829444[9] = 0;
   out_2864227840791829444[10] = 0;
   out_2864227840791829444[11] = 0;
   out_2864227840791829444[12] = 0;
   out_2864227840791829444[13] = 0;
   out_2864227840791829444[14] = 1;
   out_2864227840791829444[15] = 0;
   out_2864227840791829444[16] = 0;
   out_2864227840791829444[17] = 0;
}
void h_30(double *state, double *unused, double *out_6134652415174521657) {
   out_6134652415174521657[0] = state[4];
}
void H_30(double *state, double *unused, double *out_1824635200496754935) {
   out_1824635200496754935[0] = 0;
   out_1824635200496754935[1] = 0;
   out_1824635200496754935[2] = 0;
   out_1824635200496754935[3] = 0;
   out_1824635200496754935[4] = 1;
   out_1824635200496754935[5] = 0;
   out_1824635200496754935[6] = 0;
   out_1824635200496754935[7] = 0;
   out_1824635200496754935[8] = 0;
}
void h_26(double *state, double *unused, double *out_3515782194269032819) {
   out_3515782194269032819[0] = state[7];
}
void H_26(double *state, double *unused, double *out_4435201076884549916) {
   out_4435201076884549916[0] = 0;
   out_4435201076884549916[1] = 0;
   out_4435201076884549916[2] = 0;
   out_4435201076884549916[3] = 0;
   out_4435201076884549916[4] = 0;
   out_4435201076884549916[5] = 0;
   out_4435201076884549916[6] = 0;
   out_4435201076884549916[7] = 1;
   out_4435201076884549916[8] = 0;
}
void h_27(double *state, double *unused, double *out_5073135168339482478) {
   out_5073135168339482478[0] = state[3];
}
void H_27(double *state, double *unused, double *out_4048229271680698152) {
   out_4048229271680698152[0] = 0;
   out_4048229271680698152[1] = 0;
   out_4048229271680698152[2] = 0;
   out_4048229271680698152[3] = 1;
   out_4048229271680698152[4] = 0;
   out_4048229271680698152[5] = 0;
   out_4048229271680698152[6] = 0;
   out_4048229271680698152[7] = 0;
   out_4048229271680698152[8] = 0;
}
void h_29(double *state, double *unused, double *out_9171438466618854342) {
   out_9171438466618854342[0] = state[1];
}
void H_29(double *state, double *unused, double *out_2334866544811147119) {
   out_2334866544811147119[0] = 0;
   out_2334866544811147119[1] = 1;
   out_2334866544811147119[2] = 0;
   out_2334866544811147119[3] = 0;
   out_2334866544811147119[4] = 0;
   out_2334866544811147119[5] = 0;
   out_2334866544811147119[6] = 0;
   out_2334866544811147119[7] = 0;
   out_2334866544811147119[8] = 0;
}
void h_28(double *state, double *unused, double *out_6016645021241144913) {
   out_6016645021241144913[0] = state[0];
}
void H_28(double *state, double *unused, double *out_2747532472258383455) {
   out_2747532472258383455[0] = 1;
   out_2747532472258383455[1] = 0;
   out_2747532472258383455[2] = 0;
   out_2747532472258383455[3] = 0;
   out_2747532472258383455[4] = 0;
   out_2747532472258383455[5] = 0;
   out_2747532472258383455[6] = 0;
   out_2747532472258383455[7] = 0;
   out_2747532472258383455[8] = 0;
}
void h_31(double *state, double *unused, double *out_2311543179179655682) {
   out_2311543179179655682[0] = state[8];
}
void H_31(double *state, double *unused, double *out_5061409179117901392) {
   out_5061409179117901392[0] = 0;
   out_5061409179117901392[1] = 0;
   out_5061409179117901392[2] = 0;
   out_5061409179117901392[3] = 0;
   out_5061409179117901392[4] = 0;
   out_5061409179117901392[5] = 0;
   out_5061409179117901392[6] = 0;
   out_5061409179117901392[7] = 0;
   out_5061409179117901392[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_7751375231448978305) {
  err_fun(nom_x, delta_x, out_7751375231448978305);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_1186045100449225538) {
  inv_err_fun(nom_x, true_x, out_1186045100449225538);
}
void car_H_mod_fun(double *state, double *out_5403210608595880924) {
  H_mod_fun(state, out_5403210608595880924);
}
void car_f_fun(double *state, double dt, double *out_3846473641327680019) {
  f_fun(state,  dt, out_3846473641327680019);
}
void car_F_fun(double *state, double dt, double *out_6505574540477860652) {
  F_fun(state,  dt, out_6505574540477860652);
}
void car_h_25(double *state, double *unused, double *out_1325906349074366668) {
  h_25(state, unused, out_1325906349074366668);
}
void car_H_25(double *state, double *unused, double *out_693697758010493692) {
  H_25(state, unused, out_693697758010493692);
}
void car_h_24(double *state, double *unused, double *out_7507130987037302702) {
  h_24(state, unused, out_7507130987037302702);
}
void car_H_24(double *state, double *unused, double *out_2864227840791829444) {
  H_24(state, unused, out_2864227840791829444);
}
void car_h_30(double *state, double *unused, double *out_6134652415174521657) {
  h_30(state, unused, out_6134652415174521657);
}
void car_H_30(double *state, double *unused, double *out_1824635200496754935) {
  H_30(state, unused, out_1824635200496754935);
}
void car_h_26(double *state, double *unused, double *out_3515782194269032819) {
  h_26(state, unused, out_3515782194269032819);
}
void car_H_26(double *state, double *unused, double *out_4435201076884549916) {
  H_26(state, unused, out_4435201076884549916);
}
void car_h_27(double *state, double *unused, double *out_5073135168339482478) {
  h_27(state, unused, out_5073135168339482478);
}
void car_H_27(double *state, double *unused, double *out_4048229271680698152) {
  H_27(state, unused, out_4048229271680698152);
}
void car_h_29(double *state, double *unused, double *out_9171438466618854342) {
  h_29(state, unused, out_9171438466618854342);
}
void car_H_29(double *state, double *unused, double *out_2334866544811147119) {
  H_29(state, unused, out_2334866544811147119);
}
void car_h_28(double *state, double *unused, double *out_6016645021241144913) {
  h_28(state, unused, out_6016645021241144913);
}
void car_H_28(double *state, double *unused, double *out_2747532472258383455) {
  H_28(state, unused, out_2747532472258383455);
}
void car_h_31(double *state, double *unused, double *out_2311543179179655682) {
  h_31(state, unused, out_2311543179179655682);
}
void car_H_31(double *state, double *unused, double *out_5061409179117901392) {
  H_31(state, unused, out_5061409179117901392);
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
