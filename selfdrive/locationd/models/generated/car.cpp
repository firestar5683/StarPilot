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
void err_fun(double *nom_x, double *delta_x, double *out_3926092090457486519) {
   out_3926092090457486519[0] = delta_x[0] + nom_x[0];
   out_3926092090457486519[1] = delta_x[1] + nom_x[1];
   out_3926092090457486519[2] = delta_x[2] + nom_x[2];
   out_3926092090457486519[3] = delta_x[3] + nom_x[3];
   out_3926092090457486519[4] = delta_x[4] + nom_x[4];
   out_3926092090457486519[5] = delta_x[5] + nom_x[5];
   out_3926092090457486519[6] = delta_x[6] + nom_x[6];
   out_3926092090457486519[7] = delta_x[7] + nom_x[7];
   out_3926092090457486519[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_1042755756890972147) {
   out_1042755756890972147[0] = -nom_x[0] + true_x[0];
   out_1042755756890972147[1] = -nom_x[1] + true_x[1];
   out_1042755756890972147[2] = -nom_x[2] + true_x[2];
   out_1042755756890972147[3] = -nom_x[3] + true_x[3];
   out_1042755756890972147[4] = -nom_x[4] + true_x[4];
   out_1042755756890972147[5] = -nom_x[5] + true_x[5];
   out_1042755756890972147[6] = -nom_x[6] + true_x[6];
   out_1042755756890972147[7] = -nom_x[7] + true_x[7];
   out_1042755756890972147[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_6362512350679995207) {
   out_6362512350679995207[0] = 1.0;
   out_6362512350679995207[1] = 0.0;
   out_6362512350679995207[2] = 0.0;
   out_6362512350679995207[3] = 0.0;
   out_6362512350679995207[4] = 0.0;
   out_6362512350679995207[5] = 0.0;
   out_6362512350679995207[6] = 0.0;
   out_6362512350679995207[7] = 0.0;
   out_6362512350679995207[8] = 0.0;
   out_6362512350679995207[9] = 0.0;
   out_6362512350679995207[10] = 1.0;
   out_6362512350679995207[11] = 0.0;
   out_6362512350679995207[12] = 0.0;
   out_6362512350679995207[13] = 0.0;
   out_6362512350679995207[14] = 0.0;
   out_6362512350679995207[15] = 0.0;
   out_6362512350679995207[16] = 0.0;
   out_6362512350679995207[17] = 0.0;
   out_6362512350679995207[18] = 0.0;
   out_6362512350679995207[19] = 0.0;
   out_6362512350679995207[20] = 1.0;
   out_6362512350679995207[21] = 0.0;
   out_6362512350679995207[22] = 0.0;
   out_6362512350679995207[23] = 0.0;
   out_6362512350679995207[24] = 0.0;
   out_6362512350679995207[25] = 0.0;
   out_6362512350679995207[26] = 0.0;
   out_6362512350679995207[27] = 0.0;
   out_6362512350679995207[28] = 0.0;
   out_6362512350679995207[29] = 0.0;
   out_6362512350679995207[30] = 1.0;
   out_6362512350679995207[31] = 0.0;
   out_6362512350679995207[32] = 0.0;
   out_6362512350679995207[33] = 0.0;
   out_6362512350679995207[34] = 0.0;
   out_6362512350679995207[35] = 0.0;
   out_6362512350679995207[36] = 0.0;
   out_6362512350679995207[37] = 0.0;
   out_6362512350679995207[38] = 0.0;
   out_6362512350679995207[39] = 0.0;
   out_6362512350679995207[40] = 1.0;
   out_6362512350679995207[41] = 0.0;
   out_6362512350679995207[42] = 0.0;
   out_6362512350679995207[43] = 0.0;
   out_6362512350679995207[44] = 0.0;
   out_6362512350679995207[45] = 0.0;
   out_6362512350679995207[46] = 0.0;
   out_6362512350679995207[47] = 0.0;
   out_6362512350679995207[48] = 0.0;
   out_6362512350679995207[49] = 0.0;
   out_6362512350679995207[50] = 1.0;
   out_6362512350679995207[51] = 0.0;
   out_6362512350679995207[52] = 0.0;
   out_6362512350679995207[53] = 0.0;
   out_6362512350679995207[54] = 0.0;
   out_6362512350679995207[55] = 0.0;
   out_6362512350679995207[56] = 0.0;
   out_6362512350679995207[57] = 0.0;
   out_6362512350679995207[58] = 0.0;
   out_6362512350679995207[59] = 0.0;
   out_6362512350679995207[60] = 1.0;
   out_6362512350679995207[61] = 0.0;
   out_6362512350679995207[62] = 0.0;
   out_6362512350679995207[63] = 0.0;
   out_6362512350679995207[64] = 0.0;
   out_6362512350679995207[65] = 0.0;
   out_6362512350679995207[66] = 0.0;
   out_6362512350679995207[67] = 0.0;
   out_6362512350679995207[68] = 0.0;
   out_6362512350679995207[69] = 0.0;
   out_6362512350679995207[70] = 1.0;
   out_6362512350679995207[71] = 0.0;
   out_6362512350679995207[72] = 0.0;
   out_6362512350679995207[73] = 0.0;
   out_6362512350679995207[74] = 0.0;
   out_6362512350679995207[75] = 0.0;
   out_6362512350679995207[76] = 0.0;
   out_6362512350679995207[77] = 0.0;
   out_6362512350679995207[78] = 0.0;
   out_6362512350679995207[79] = 0.0;
   out_6362512350679995207[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_424859049759384026) {
   out_424859049759384026[0] = state[0];
   out_424859049759384026[1] = state[1];
   out_424859049759384026[2] = state[2];
   out_424859049759384026[3] = state[3];
   out_424859049759384026[4] = state[4];
   out_424859049759384026[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_424859049759384026[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_424859049759384026[7] = state[7];
   out_424859049759384026[8] = state[8];
}
void F_fun(double *state, double dt, double *out_5354778108929478985) {
   out_5354778108929478985[0] = 1;
   out_5354778108929478985[1] = 0;
   out_5354778108929478985[2] = 0;
   out_5354778108929478985[3] = 0;
   out_5354778108929478985[4] = 0;
   out_5354778108929478985[5] = 0;
   out_5354778108929478985[6] = 0;
   out_5354778108929478985[7] = 0;
   out_5354778108929478985[8] = 0;
   out_5354778108929478985[9] = 0;
   out_5354778108929478985[10] = 1;
   out_5354778108929478985[11] = 0;
   out_5354778108929478985[12] = 0;
   out_5354778108929478985[13] = 0;
   out_5354778108929478985[14] = 0;
   out_5354778108929478985[15] = 0;
   out_5354778108929478985[16] = 0;
   out_5354778108929478985[17] = 0;
   out_5354778108929478985[18] = 0;
   out_5354778108929478985[19] = 0;
   out_5354778108929478985[20] = 1;
   out_5354778108929478985[21] = 0;
   out_5354778108929478985[22] = 0;
   out_5354778108929478985[23] = 0;
   out_5354778108929478985[24] = 0;
   out_5354778108929478985[25] = 0;
   out_5354778108929478985[26] = 0;
   out_5354778108929478985[27] = 0;
   out_5354778108929478985[28] = 0;
   out_5354778108929478985[29] = 0;
   out_5354778108929478985[30] = 1;
   out_5354778108929478985[31] = 0;
   out_5354778108929478985[32] = 0;
   out_5354778108929478985[33] = 0;
   out_5354778108929478985[34] = 0;
   out_5354778108929478985[35] = 0;
   out_5354778108929478985[36] = 0;
   out_5354778108929478985[37] = 0;
   out_5354778108929478985[38] = 0;
   out_5354778108929478985[39] = 0;
   out_5354778108929478985[40] = 1;
   out_5354778108929478985[41] = 0;
   out_5354778108929478985[42] = 0;
   out_5354778108929478985[43] = 0;
   out_5354778108929478985[44] = 0;
   out_5354778108929478985[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_5354778108929478985[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_5354778108929478985[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_5354778108929478985[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_5354778108929478985[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_5354778108929478985[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_5354778108929478985[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_5354778108929478985[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_5354778108929478985[53] = -9.8100000000000005*dt;
   out_5354778108929478985[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_5354778108929478985[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_5354778108929478985[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_5354778108929478985[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_5354778108929478985[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_5354778108929478985[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_5354778108929478985[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_5354778108929478985[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_5354778108929478985[62] = 0;
   out_5354778108929478985[63] = 0;
   out_5354778108929478985[64] = 0;
   out_5354778108929478985[65] = 0;
   out_5354778108929478985[66] = 0;
   out_5354778108929478985[67] = 0;
   out_5354778108929478985[68] = 0;
   out_5354778108929478985[69] = 0;
   out_5354778108929478985[70] = 1;
   out_5354778108929478985[71] = 0;
   out_5354778108929478985[72] = 0;
   out_5354778108929478985[73] = 0;
   out_5354778108929478985[74] = 0;
   out_5354778108929478985[75] = 0;
   out_5354778108929478985[76] = 0;
   out_5354778108929478985[77] = 0;
   out_5354778108929478985[78] = 0;
   out_5354778108929478985[79] = 0;
   out_5354778108929478985[80] = 1;
}
void h_25(double *state, double *unused, double *out_2030817843873969747) {
   out_2030817843873969747[0] = state[6];
}
void H_25(double *state, double *unused, double *out_8509671287957375619) {
   out_8509671287957375619[0] = 0;
   out_8509671287957375619[1] = 0;
   out_8509671287957375619[2] = 0;
   out_8509671287957375619[3] = 0;
   out_8509671287957375619[4] = 0;
   out_8509671287957375619[5] = 0;
   out_8509671287957375619[6] = 1;
   out_8509671287957375619[7] = 0;
   out_8509671287957375619[8] = 0;
}
void h_24(double *state, double *unused, double *out_6573865906285076625) {
   out_6573865906285076625[0] = state[4];
   out_6573865906285076625[1] = state[5];
}
void H_24(double *state, double *unused, double *out_1855465829849189862) {
   out_1855465829849189862[0] = 0;
   out_1855465829849189862[1] = 0;
   out_1855465829849189862[2] = 0;
   out_1855465829849189862[3] = 0;
   out_1855465829849189862[4] = 1;
   out_1855465829849189862[5] = 0;
   out_1855465829849189862[6] = 0;
   out_1855465829849189862[7] = 0;
   out_1855465829849189862[8] = 0;
   out_1855465829849189862[9] = 0;
   out_1855465829849189862[10] = 0;
   out_1855465829849189862[11] = 0;
   out_1855465829849189862[12] = 0;
   out_1855465829849189862[13] = 0;
   out_1855465829849189862[14] = 1;
   out_1855465829849189862[15] = 0;
   out_1855465829849189862[16] = 0;
   out_1855465829849189862[17] = 0;
}
void h_30(double *state, double *unused, double *out_8801653070224320683) {
   out_8801653070224320683[0] = state[4];
}
void H_30(double *state, double *unused, double *out_8639010235100615689) {
   out_8639010235100615689[0] = 0;
   out_8639010235100615689[1] = 0;
   out_8639010235100615689[2] = 0;
   out_8639010235100615689[3] = 0;
   out_8639010235100615689[4] = 1;
   out_8639010235100615689[5] = 0;
   out_8639010235100615689[6] = 0;
   out_8639010235100615689[7] = 0;
   out_8639010235100615689[8] = 0;
}
void h_26(double *state, double *unused, double *out_7111205235488639723) {
   out_7111205235488639723[0] = state[7];
}
void H_26(double *state, double *unused, double *out_6195569466878119773) {
   out_6195569466878119773[0] = 0;
   out_6195569466878119773[1] = 0;
   out_6195569466878119773[2] = 0;
   out_6195569466878119773[3] = 0;
   out_6195569466878119773[4] = 0;
   out_6195569466878119773[5] = 0;
   out_6195569466878119773[6] = 0;
   out_6195569466878119773[7] = 1;
   out_6195569466878119773[8] = 0;
}
void h_27(double *state, double *unused, double *out_3114072219241677790) {
   out_3114072219241677790[0] = state[3];
}
void H_27(double *state, double *unused, double *out_7632970526808511016) {
   out_7632970526808511016[0] = 0;
   out_7632970526808511016[1] = 0;
   out_7632970526808511016[2] = 0;
   out_7632970526808511016[3] = 1;
   out_7632970526808511016[4] = 0;
   out_7632970526808511016[5] = 0;
   out_7632970526808511016[6] = 0;
   out_7632970526808511016[7] = 0;
   out_7632970526808511016[8] = 0;
}
void h_29(double *state, double *unused, double *out_3799979802563475038) {
   out_3799979802563475038[0] = state[1];
}
void H_29(double *state, double *unused, double *out_8128778890786223505) {
   out_8128778890786223505[0] = 0;
   out_8128778890786223505[1] = 1;
   out_8128778890786223505[2] = 0;
   out_8128778890786223505[3] = 0;
   out_8128778890786223505[4] = 0;
   out_8128778890786223505[5] = 0;
   out_8128778890786223505[6] = 0;
   out_8128778890786223505[7] = 0;
   out_8128778890786223505[8] = 0;
}
void h_28(double *state, double *unused, double *out_2027345570885213463) {
   out_2027345570885213463[0] = state[0];
}
void H_28(double *state, double *unused, double *out_5235566165853797537) {
   out_5235566165853797537[0] = 1;
   out_5235566165853797537[1] = 0;
   out_5235566165853797537[2] = 0;
   out_5235566165853797537[3] = 0;
   out_5235566165853797537[4] = 0;
   out_5235566165853797537[5] = 0;
   out_5235566165853797537[6] = 0;
   out_5235566165853797537[7] = 0;
   out_5235566165853797537[8] = 0;
}
void h_31(double *state, double *unused, double *out_5732447412946702694) {
   out_5732447412946702694[0] = state[8];
}
void H_31(double *state, double *unused, double *out_8479025326080415191) {
   out_8479025326080415191[0] = 0;
   out_8479025326080415191[1] = 0;
   out_8479025326080415191[2] = 0;
   out_8479025326080415191[3] = 0;
   out_8479025326080415191[4] = 0;
   out_8479025326080415191[5] = 0;
   out_8479025326080415191[6] = 0;
   out_8479025326080415191[7] = 0;
   out_8479025326080415191[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_3926092090457486519) {
  err_fun(nom_x, delta_x, out_3926092090457486519);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_1042755756890972147) {
  inv_err_fun(nom_x, true_x, out_1042755756890972147);
}
void car_H_mod_fun(double *state, double *out_6362512350679995207) {
  H_mod_fun(state, out_6362512350679995207);
}
void car_f_fun(double *state, double dt, double *out_424859049759384026) {
  f_fun(state,  dt, out_424859049759384026);
}
void car_F_fun(double *state, double dt, double *out_5354778108929478985) {
  F_fun(state,  dt, out_5354778108929478985);
}
void car_h_25(double *state, double *unused, double *out_2030817843873969747) {
  h_25(state, unused, out_2030817843873969747);
}
void car_H_25(double *state, double *unused, double *out_8509671287957375619) {
  H_25(state, unused, out_8509671287957375619);
}
void car_h_24(double *state, double *unused, double *out_6573865906285076625) {
  h_24(state, unused, out_6573865906285076625);
}
void car_H_24(double *state, double *unused, double *out_1855465829849189862) {
  H_24(state, unused, out_1855465829849189862);
}
void car_h_30(double *state, double *unused, double *out_8801653070224320683) {
  h_30(state, unused, out_8801653070224320683);
}
void car_H_30(double *state, double *unused, double *out_8639010235100615689) {
  H_30(state, unused, out_8639010235100615689);
}
void car_h_26(double *state, double *unused, double *out_7111205235488639723) {
  h_26(state, unused, out_7111205235488639723);
}
void car_H_26(double *state, double *unused, double *out_6195569466878119773) {
  H_26(state, unused, out_6195569466878119773);
}
void car_h_27(double *state, double *unused, double *out_3114072219241677790) {
  h_27(state, unused, out_3114072219241677790);
}
void car_H_27(double *state, double *unused, double *out_7632970526808511016) {
  H_27(state, unused, out_7632970526808511016);
}
void car_h_29(double *state, double *unused, double *out_3799979802563475038) {
  h_29(state, unused, out_3799979802563475038);
}
void car_H_29(double *state, double *unused, double *out_8128778890786223505) {
  H_29(state, unused, out_8128778890786223505);
}
void car_h_28(double *state, double *unused, double *out_2027345570885213463) {
  h_28(state, unused, out_2027345570885213463);
}
void car_H_28(double *state, double *unused, double *out_5235566165853797537) {
  H_28(state, unused, out_5235566165853797537);
}
void car_h_31(double *state, double *unused, double *out_5732447412946702694) {
  h_31(state, unused, out_5732447412946702694);
}
void car_H_31(double *state, double *unused, double *out_8479025326080415191) {
  H_31(state, unused, out_8479025326080415191);
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
