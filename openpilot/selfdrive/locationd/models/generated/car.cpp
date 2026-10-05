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
void err_fun(double *nom_x, double *delta_x, double *out_6883645272193254700) {
   out_6883645272193254700[0] = delta_x[0] + nom_x[0];
   out_6883645272193254700[1] = delta_x[1] + nom_x[1];
   out_6883645272193254700[2] = delta_x[2] + nom_x[2];
   out_6883645272193254700[3] = delta_x[3] + nom_x[3];
   out_6883645272193254700[4] = delta_x[4] + nom_x[4];
   out_6883645272193254700[5] = delta_x[5] + nom_x[5];
   out_6883645272193254700[6] = delta_x[6] + nom_x[6];
   out_6883645272193254700[7] = delta_x[7] + nom_x[7];
   out_6883645272193254700[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_7270792730127520500) {
   out_7270792730127520500[0] = -nom_x[0] + true_x[0];
   out_7270792730127520500[1] = -nom_x[1] + true_x[1];
   out_7270792730127520500[2] = -nom_x[2] + true_x[2];
   out_7270792730127520500[3] = -nom_x[3] + true_x[3];
   out_7270792730127520500[4] = -nom_x[4] + true_x[4];
   out_7270792730127520500[5] = -nom_x[5] + true_x[5];
   out_7270792730127520500[6] = -nom_x[6] + true_x[6];
   out_7270792730127520500[7] = -nom_x[7] + true_x[7];
   out_7270792730127520500[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_6693185596112580113) {
   out_6693185596112580113[0] = 1.0;
   out_6693185596112580113[1] = 0.0;
   out_6693185596112580113[2] = 0.0;
   out_6693185596112580113[3] = 0.0;
   out_6693185596112580113[4] = 0.0;
   out_6693185596112580113[5] = 0.0;
   out_6693185596112580113[6] = 0.0;
   out_6693185596112580113[7] = 0.0;
   out_6693185596112580113[8] = 0.0;
   out_6693185596112580113[9] = 0.0;
   out_6693185596112580113[10] = 1.0;
   out_6693185596112580113[11] = 0.0;
   out_6693185596112580113[12] = 0.0;
   out_6693185596112580113[13] = 0.0;
   out_6693185596112580113[14] = 0.0;
   out_6693185596112580113[15] = 0.0;
   out_6693185596112580113[16] = 0.0;
   out_6693185596112580113[17] = 0.0;
   out_6693185596112580113[18] = 0.0;
   out_6693185596112580113[19] = 0.0;
   out_6693185596112580113[20] = 1.0;
   out_6693185596112580113[21] = 0.0;
   out_6693185596112580113[22] = 0.0;
   out_6693185596112580113[23] = 0.0;
   out_6693185596112580113[24] = 0.0;
   out_6693185596112580113[25] = 0.0;
   out_6693185596112580113[26] = 0.0;
   out_6693185596112580113[27] = 0.0;
   out_6693185596112580113[28] = 0.0;
   out_6693185596112580113[29] = 0.0;
   out_6693185596112580113[30] = 1.0;
   out_6693185596112580113[31] = 0.0;
   out_6693185596112580113[32] = 0.0;
   out_6693185596112580113[33] = 0.0;
   out_6693185596112580113[34] = 0.0;
   out_6693185596112580113[35] = 0.0;
   out_6693185596112580113[36] = 0.0;
   out_6693185596112580113[37] = 0.0;
   out_6693185596112580113[38] = 0.0;
   out_6693185596112580113[39] = 0.0;
   out_6693185596112580113[40] = 1.0;
   out_6693185596112580113[41] = 0.0;
   out_6693185596112580113[42] = 0.0;
   out_6693185596112580113[43] = 0.0;
   out_6693185596112580113[44] = 0.0;
   out_6693185596112580113[45] = 0.0;
   out_6693185596112580113[46] = 0.0;
   out_6693185596112580113[47] = 0.0;
   out_6693185596112580113[48] = 0.0;
   out_6693185596112580113[49] = 0.0;
   out_6693185596112580113[50] = 1.0;
   out_6693185596112580113[51] = 0.0;
   out_6693185596112580113[52] = 0.0;
   out_6693185596112580113[53] = 0.0;
   out_6693185596112580113[54] = 0.0;
   out_6693185596112580113[55] = 0.0;
   out_6693185596112580113[56] = 0.0;
   out_6693185596112580113[57] = 0.0;
   out_6693185596112580113[58] = 0.0;
   out_6693185596112580113[59] = 0.0;
   out_6693185596112580113[60] = 1.0;
   out_6693185596112580113[61] = 0.0;
   out_6693185596112580113[62] = 0.0;
   out_6693185596112580113[63] = 0.0;
   out_6693185596112580113[64] = 0.0;
   out_6693185596112580113[65] = 0.0;
   out_6693185596112580113[66] = 0.0;
   out_6693185596112580113[67] = 0.0;
   out_6693185596112580113[68] = 0.0;
   out_6693185596112580113[69] = 0.0;
   out_6693185596112580113[70] = 1.0;
   out_6693185596112580113[71] = 0.0;
   out_6693185596112580113[72] = 0.0;
   out_6693185596112580113[73] = 0.0;
   out_6693185596112580113[74] = 0.0;
   out_6693185596112580113[75] = 0.0;
   out_6693185596112580113[76] = 0.0;
   out_6693185596112580113[77] = 0.0;
   out_6693185596112580113[78] = 0.0;
   out_6693185596112580113[79] = 0.0;
   out_6693185596112580113[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_8543617912068228194) {
   out_8543617912068228194[0] = state[0];
   out_8543617912068228194[1] = state[1];
   out_8543617912068228194[2] = state[2];
   out_8543617912068228194[3] = state[3];
   out_8543617912068228194[4] = state[4];
   out_8543617912068228194[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_8543617912068228194[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_8543617912068228194[7] = state[7];
   out_8543617912068228194[8] = state[8];
}
void F_fun(double *state, double dt, double *out_1180522696706183383) {
   out_1180522696706183383[0] = 1;
   out_1180522696706183383[1] = 0;
   out_1180522696706183383[2] = 0;
   out_1180522696706183383[3] = 0;
   out_1180522696706183383[4] = 0;
   out_1180522696706183383[5] = 0;
   out_1180522696706183383[6] = 0;
   out_1180522696706183383[7] = 0;
   out_1180522696706183383[8] = 0;
   out_1180522696706183383[9] = 0;
   out_1180522696706183383[10] = 1;
   out_1180522696706183383[11] = 0;
   out_1180522696706183383[12] = 0;
   out_1180522696706183383[13] = 0;
   out_1180522696706183383[14] = 0;
   out_1180522696706183383[15] = 0;
   out_1180522696706183383[16] = 0;
   out_1180522696706183383[17] = 0;
   out_1180522696706183383[18] = 0;
   out_1180522696706183383[19] = 0;
   out_1180522696706183383[20] = 1;
   out_1180522696706183383[21] = 0;
   out_1180522696706183383[22] = 0;
   out_1180522696706183383[23] = 0;
   out_1180522696706183383[24] = 0;
   out_1180522696706183383[25] = 0;
   out_1180522696706183383[26] = 0;
   out_1180522696706183383[27] = 0;
   out_1180522696706183383[28] = 0;
   out_1180522696706183383[29] = 0;
   out_1180522696706183383[30] = 1;
   out_1180522696706183383[31] = 0;
   out_1180522696706183383[32] = 0;
   out_1180522696706183383[33] = 0;
   out_1180522696706183383[34] = 0;
   out_1180522696706183383[35] = 0;
   out_1180522696706183383[36] = 0;
   out_1180522696706183383[37] = 0;
   out_1180522696706183383[38] = 0;
   out_1180522696706183383[39] = 0;
   out_1180522696706183383[40] = 1;
   out_1180522696706183383[41] = 0;
   out_1180522696706183383[42] = 0;
   out_1180522696706183383[43] = 0;
   out_1180522696706183383[44] = 0;
   out_1180522696706183383[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_1180522696706183383[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_1180522696706183383[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_1180522696706183383[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_1180522696706183383[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_1180522696706183383[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_1180522696706183383[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_1180522696706183383[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_1180522696706183383[53] = -9.8100000000000005*dt;
   out_1180522696706183383[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_1180522696706183383[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_1180522696706183383[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_1180522696706183383[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_1180522696706183383[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_1180522696706183383[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_1180522696706183383[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_1180522696706183383[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_1180522696706183383[62] = 0;
   out_1180522696706183383[63] = 0;
   out_1180522696706183383[64] = 0;
   out_1180522696706183383[65] = 0;
   out_1180522696706183383[66] = 0;
   out_1180522696706183383[67] = 0;
   out_1180522696706183383[68] = 0;
   out_1180522696706183383[69] = 0;
   out_1180522696706183383[70] = 1;
   out_1180522696706183383[71] = 0;
   out_1180522696706183383[72] = 0;
   out_1180522696706183383[73] = 0;
   out_1180522696706183383[74] = 0;
   out_1180522696706183383[75] = 0;
   out_1180522696706183383[76] = 0;
   out_1180522696706183383[77] = 0;
   out_1180522696706183383[78] = 0;
   out_1180522696706183383[79] = 0;
   out_1180522696706183383[80] = 1;
}
void h_25(double *state, double *unused, double *out_6701820119749264759) {
   out_6701820119749264759[0] = state[6];
}
void H_25(double *state, double *unused, double *out_8659540204804574995) {
   out_8659540204804574995[0] = 0;
   out_8659540204804574995[1] = 0;
   out_8659540204804574995[2] = 0;
   out_8659540204804574995[3] = 0;
   out_8659540204804574995[4] = 0;
   out_8659540204804574995[5] = 0;
   out_8659540204804574995[6] = 1;
   out_8659540204804574995[7] = 0;
   out_8659540204804574995[8] = 0;
}
void h_24(double *state, double *unused, double *out_1034044246016650253) {
   out_1034044246016650253[0] = state[4];
   out_1034044246016650253[1] = state[5];
}
void H_24(double *state, double *unused, double *out_568524981264620230) {
   out_568524981264620230[0] = 0;
   out_568524981264620230[1] = 0;
   out_568524981264620230[2] = 0;
   out_568524981264620230[3] = 0;
   out_568524981264620230[4] = 1;
   out_568524981264620230[5] = 0;
   out_568524981264620230[6] = 0;
   out_568524981264620230[7] = 0;
   out_568524981264620230[8] = 0;
   out_568524981264620230[9] = 0;
   out_568524981264620230[10] = 0;
   out_568524981264620230[11] = 0;
   out_568524981264620230[12] = 0;
   out_568524981264620230[13] = 0;
   out_568524981264620230[14] = 1;
   out_568524981264620230[15] = 0;
   out_568524981264620230[16] = 0;
   out_568524981264620230[17] = 0;
}
void h_30(double *state, double *unused, double *out_3064370591495242409) {
   out_3064370591495242409[0] = state[4];
}
void H_30(double *state, double *unused, double *out_5259507538777368423) {
   out_5259507538777368423[0] = 0;
   out_5259507538777368423[1] = 0;
   out_5259507538777368423[2] = 0;
   out_5259507538777368423[3] = 0;
   out_5259507538777368423[4] = 1;
   out_5259507538777368423[5] = 0;
   out_5259507538777368423[6] = 0;
   out_5259507538777368423[7] = 0;
   out_5259507538777368423[8] = 0;
}
void h_26(double *state, double *unused, double *out_4370772842933458404) {
   out_4370772842933458404[0] = state[7];
}
void H_26(double *state, double *unused, double *out_6045700550030920397) {
   out_6045700550030920397[0] = 0;
   out_6045700550030920397[1] = 0;
   out_6045700550030920397[2] = 0;
   out_6045700550030920397[3] = 0;
   out_6045700550030920397[4] = 0;
   out_6045700550030920397[5] = 0;
   out_6045700550030920397[6] = 0;
   out_6045700550030920397[7] = 1;
   out_6045700550030920397[8] = 0;
}
void h_27(double *state, double *unused, double *out_2094489344516732381) {
   out_2094489344516732381[0] = state[3];
}
void H_27(double *state, double *unused, double *out_3084744226976943512) {
   out_3084744226976943512[0] = 0;
   out_3084744226976943512[1] = 0;
   out_3084744226976943512[2] = 0;
   out_3084744226976943512[3] = 1;
   out_3084744226976943512[4] = 0;
   out_3084744226976943512[5] = 0;
   out_3084744226976943512[6] = 0;
   out_3084744226976943512[7] = 0;
   out_3084744226976943512[8] = 0;
}
void h_29(double *state, double *unused, double *out_1937302676165603236) {
   out_1937302676165603236[0] = state[1];
}
void H_29(double *state, double *unused, double *out_5769738883091760607) {
   out_5769738883091760607[0] = 0;
   out_5769738883091760607[1] = 1;
   out_5769738883091760607[2] = 0;
   out_5769738883091760607[3] = 0;
   out_5769738883091760607[4] = 0;
   out_5769738883091760607[5] = 0;
   out_5769738883091760607[6] = 0;
   out_5769738883091760607[7] = 0;
   out_5769738883091760607[8] = 0;
}
void h_28(double *state, double *unused, double *out_6887479827490108384) {
   out_6887479827490108384[0] = state[0];
}
void H_28(double *state, double *unused, double *out_687339866022230033) {
   out_687339866022230033[0] = 1;
   out_687339866022230033[1] = 0;
   out_687339866022230033[2] = 0;
   out_687339866022230033[3] = 0;
   out_687339866022230033[4] = 0;
   out_687339866022230033[5] = 0;
   out_687339866022230033[6] = 0;
   out_687339866022230033[7] = 0;
   out_687339866022230033[8] = 0;
}
void h_31(double *state, double *unused, double *out_3863651303206237672) {
   out_3863651303206237672[0] = state[8];
}
void H_31(double *state, double *unused, double *out_5419492447797568921) {
   out_5419492447797568921[0] = 0;
   out_5419492447797568921[1] = 0;
   out_5419492447797568921[2] = 0;
   out_5419492447797568921[3] = 0;
   out_5419492447797568921[4] = 0;
   out_5419492447797568921[5] = 0;
   out_5419492447797568921[6] = 0;
   out_5419492447797568921[7] = 0;
   out_5419492447797568921[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_6883645272193254700) {
  err_fun(nom_x, delta_x, out_6883645272193254700);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_7270792730127520500) {
  inv_err_fun(nom_x, true_x, out_7270792730127520500);
}
void car_H_mod_fun(double *state, double *out_6693185596112580113) {
  H_mod_fun(state, out_6693185596112580113);
}
void car_f_fun(double *state, double dt, double *out_8543617912068228194) {
  f_fun(state,  dt, out_8543617912068228194);
}
void car_F_fun(double *state, double dt, double *out_1180522696706183383) {
  F_fun(state,  dt, out_1180522696706183383);
}
void car_h_25(double *state, double *unused, double *out_6701820119749264759) {
  h_25(state, unused, out_6701820119749264759);
}
void car_H_25(double *state, double *unused, double *out_8659540204804574995) {
  H_25(state, unused, out_8659540204804574995);
}
void car_h_24(double *state, double *unused, double *out_1034044246016650253) {
  h_24(state, unused, out_1034044246016650253);
}
void car_H_24(double *state, double *unused, double *out_568524981264620230) {
  H_24(state, unused, out_568524981264620230);
}
void car_h_30(double *state, double *unused, double *out_3064370591495242409) {
  h_30(state, unused, out_3064370591495242409);
}
void car_H_30(double *state, double *unused, double *out_5259507538777368423) {
  H_30(state, unused, out_5259507538777368423);
}
void car_h_26(double *state, double *unused, double *out_4370772842933458404) {
  h_26(state, unused, out_4370772842933458404);
}
void car_H_26(double *state, double *unused, double *out_6045700550030920397) {
  H_26(state, unused, out_6045700550030920397);
}
void car_h_27(double *state, double *unused, double *out_2094489344516732381) {
  h_27(state, unused, out_2094489344516732381);
}
void car_H_27(double *state, double *unused, double *out_3084744226976943512) {
  H_27(state, unused, out_3084744226976943512);
}
void car_h_29(double *state, double *unused, double *out_1937302676165603236) {
  h_29(state, unused, out_1937302676165603236);
}
void car_H_29(double *state, double *unused, double *out_5769738883091760607) {
  H_29(state, unused, out_5769738883091760607);
}
void car_h_28(double *state, double *unused, double *out_6887479827490108384) {
  h_28(state, unused, out_6887479827490108384);
}
void car_H_28(double *state, double *unused, double *out_687339866022230033) {
  H_28(state, unused, out_687339866022230033);
}
void car_h_31(double *state, double *unused, double *out_3863651303206237672) {
  h_31(state, unused, out_3863651303206237672);
}
void car_H_31(double *state, double *unused, double *out_5419492447797568921) {
  H_31(state, unused, out_5419492447797568921);
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
