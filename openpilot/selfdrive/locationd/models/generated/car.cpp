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
void err_fun(double *nom_x, double *delta_x, double *out_4652830232542905037) {
   out_4652830232542905037[0] = delta_x[0] + nom_x[0];
   out_4652830232542905037[1] = delta_x[1] + nom_x[1];
   out_4652830232542905037[2] = delta_x[2] + nom_x[2];
   out_4652830232542905037[3] = delta_x[3] + nom_x[3];
   out_4652830232542905037[4] = delta_x[4] + nom_x[4];
   out_4652830232542905037[5] = delta_x[5] + nom_x[5];
   out_4652830232542905037[6] = delta_x[6] + nom_x[6];
   out_4652830232542905037[7] = delta_x[7] + nom_x[7];
   out_4652830232542905037[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_3291886134262608133) {
   out_3291886134262608133[0] = -nom_x[0] + true_x[0];
   out_3291886134262608133[1] = -nom_x[1] + true_x[1];
   out_3291886134262608133[2] = -nom_x[2] + true_x[2];
   out_3291886134262608133[3] = -nom_x[3] + true_x[3];
   out_3291886134262608133[4] = -nom_x[4] + true_x[4];
   out_3291886134262608133[5] = -nom_x[5] + true_x[5];
   out_3291886134262608133[6] = -nom_x[6] + true_x[6];
   out_3291886134262608133[7] = -nom_x[7] + true_x[7];
   out_3291886134262608133[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_4576150220690732126) {
   out_4576150220690732126[0] = 1.0;
   out_4576150220690732126[1] = 0.0;
   out_4576150220690732126[2] = 0.0;
   out_4576150220690732126[3] = 0.0;
   out_4576150220690732126[4] = 0.0;
   out_4576150220690732126[5] = 0.0;
   out_4576150220690732126[6] = 0.0;
   out_4576150220690732126[7] = 0.0;
   out_4576150220690732126[8] = 0.0;
   out_4576150220690732126[9] = 0.0;
   out_4576150220690732126[10] = 1.0;
   out_4576150220690732126[11] = 0.0;
   out_4576150220690732126[12] = 0.0;
   out_4576150220690732126[13] = 0.0;
   out_4576150220690732126[14] = 0.0;
   out_4576150220690732126[15] = 0.0;
   out_4576150220690732126[16] = 0.0;
   out_4576150220690732126[17] = 0.0;
   out_4576150220690732126[18] = 0.0;
   out_4576150220690732126[19] = 0.0;
   out_4576150220690732126[20] = 1.0;
   out_4576150220690732126[21] = 0.0;
   out_4576150220690732126[22] = 0.0;
   out_4576150220690732126[23] = 0.0;
   out_4576150220690732126[24] = 0.0;
   out_4576150220690732126[25] = 0.0;
   out_4576150220690732126[26] = 0.0;
   out_4576150220690732126[27] = 0.0;
   out_4576150220690732126[28] = 0.0;
   out_4576150220690732126[29] = 0.0;
   out_4576150220690732126[30] = 1.0;
   out_4576150220690732126[31] = 0.0;
   out_4576150220690732126[32] = 0.0;
   out_4576150220690732126[33] = 0.0;
   out_4576150220690732126[34] = 0.0;
   out_4576150220690732126[35] = 0.0;
   out_4576150220690732126[36] = 0.0;
   out_4576150220690732126[37] = 0.0;
   out_4576150220690732126[38] = 0.0;
   out_4576150220690732126[39] = 0.0;
   out_4576150220690732126[40] = 1.0;
   out_4576150220690732126[41] = 0.0;
   out_4576150220690732126[42] = 0.0;
   out_4576150220690732126[43] = 0.0;
   out_4576150220690732126[44] = 0.0;
   out_4576150220690732126[45] = 0.0;
   out_4576150220690732126[46] = 0.0;
   out_4576150220690732126[47] = 0.0;
   out_4576150220690732126[48] = 0.0;
   out_4576150220690732126[49] = 0.0;
   out_4576150220690732126[50] = 1.0;
   out_4576150220690732126[51] = 0.0;
   out_4576150220690732126[52] = 0.0;
   out_4576150220690732126[53] = 0.0;
   out_4576150220690732126[54] = 0.0;
   out_4576150220690732126[55] = 0.0;
   out_4576150220690732126[56] = 0.0;
   out_4576150220690732126[57] = 0.0;
   out_4576150220690732126[58] = 0.0;
   out_4576150220690732126[59] = 0.0;
   out_4576150220690732126[60] = 1.0;
   out_4576150220690732126[61] = 0.0;
   out_4576150220690732126[62] = 0.0;
   out_4576150220690732126[63] = 0.0;
   out_4576150220690732126[64] = 0.0;
   out_4576150220690732126[65] = 0.0;
   out_4576150220690732126[66] = 0.0;
   out_4576150220690732126[67] = 0.0;
   out_4576150220690732126[68] = 0.0;
   out_4576150220690732126[69] = 0.0;
   out_4576150220690732126[70] = 1.0;
   out_4576150220690732126[71] = 0.0;
   out_4576150220690732126[72] = 0.0;
   out_4576150220690732126[73] = 0.0;
   out_4576150220690732126[74] = 0.0;
   out_4576150220690732126[75] = 0.0;
   out_4576150220690732126[76] = 0.0;
   out_4576150220690732126[77] = 0.0;
   out_4576150220690732126[78] = 0.0;
   out_4576150220690732126[79] = 0.0;
   out_4576150220690732126[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_829378765985642412) {
   out_829378765985642412[0] = state[0];
   out_829378765985642412[1] = state[1];
   out_829378765985642412[2] = state[2];
   out_829378765985642412[3] = state[3];
   out_829378765985642412[4] = state[4];
   out_829378765985642412[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_829378765985642412[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_829378765985642412[7] = state[7];
   out_829378765985642412[8] = state[8];
}
void F_fun(double *state, double dt, double *out_5290468730257954652) {
   out_5290468730257954652[0] = 1;
   out_5290468730257954652[1] = 0;
   out_5290468730257954652[2] = 0;
   out_5290468730257954652[3] = 0;
   out_5290468730257954652[4] = 0;
   out_5290468730257954652[5] = 0;
   out_5290468730257954652[6] = 0;
   out_5290468730257954652[7] = 0;
   out_5290468730257954652[8] = 0;
   out_5290468730257954652[9] = 0;
   out_5290468730257954652[10] = 1;
   out_5290468730257954652[11] = 0;
   out_5290468730257954652[12] = 0;
   out_5290468730257954652[13] = 0;
   out_5290468730257954652[14] = 0;
   out_5290468730257954652[15] = 0;
   out_5290468730257954652[16] = 0;
   out_5290468730257954652[17] = 0;
   out_5290468730257954652[18] = 0;
   out_5290468730257954652[19] = 0;
   out_5290468730257954652[20] = 1;
   out_5290468730257954652[21] = 0;
   out_5290468730257954652[22] = 0;
   out_5290468730257954652[23] = 0;
   out_5290468730257954652[24] = 0;
   out_5290468730257954652[25] = 0;
   out_5290468730257954652[26] = 0;
   out_5290468730257954652[27] = 0;
   out_5290468730257954652[28] = 0;
   out_5290468730257954652[29] = 0;
   out_5290468730257954652[30] = 1;
   out_5290468730257954652[31] = 0;
   out_5290468730257954652[32] = 0;
   out_5290468730257954652[33] = 0;
   out_5290468730257954652[34] = 0;
   out_5290468730257954652[35] = 0;
   out_5290468730257954652[36] = 0;
   out_5290468730257954652[37] = 0;
   out_5290468730257954652[38] = 0;
   out_5290468730257954652[39] = 0;
   out_5290468730257954652[40] = 1;
   out_5290468730257954652[41] = 0;
   out_5290468730257954652[42] = 0;
   out_5290468730257954652[43] = 0;
   out_5290468730257954652[44] = 0;
   out_5290468730257954652[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_5290468730257954652[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_5290468730257954652[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_5290468730257954652[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_5290468730257954652[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_5290468730257954652[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_5290468730257954652[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_5290468730257954652[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_5290468730257954652[53] = -9.8100000000000005*dt;
   out_5290468730257954652[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_5290468730257954652[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_5290468730257954652[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_5290468730257954652[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_5290468730257954652[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_5290468730257954652[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_5290468730257954652[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_5290468730257954652[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_5290468730257954652[62] = 0;
   out_5290468730257954652[63] = 0;
   out_5290468730257954652[64] = 0;
   out_5290468730257954652[65] = 0;
   out_5290468730257954652[66] = 0;
   out_5290468730257954652[67] = 0;
   out_5290468730257954652[68] = 0;
   out_5290468730257954652[69] = 0;
   out_5290468730257954652[70] = 1;
   out_5290468730257954652[71] = 0;
   out_5290468730257954652[72] = 0;
   out_5290468730257954652[73] = 0;
   out_5290468730257954652[74] = 0;
   out_5290468730257954652[75] = 0;
   out_5290468730257954652[76] = 0;
   out_5290468730257954652[77] = 0;
   out_5290468730257954652[78] = 0;
   out_5290468730257954652[79] = 0;
   out_5290468730257954652[80] = 1;
}
void h_25(double *state, double *unused, double *out_1533454437622332874) {
   out_1533454437622332874[0] = state[6];
}
void H_25(double *state, double *unused, double *out_327541604493932714) {
   out_327541604493932714[0] = 0;
   out_327541604493932714[1] = 0;
   out_327541604493932714[2] = 0;
   out_327541604493932714[3] = 0;
   out_327541604493932714[4] = 0;
   out_327541604493932714[5] = 0;
   out_327541604493932714[6] = 1;
   out_327541604493932714[7] = 0;
   out_327541604493932714[8] = 0;
}
void h_24(double *state, double *unused, double *out_5835817958400148077) {
   out_5835817958400148077[0] = state[4];
   out_5835817958400148077[1] = state[5];
}
void H_24(double *state, double *unused, double *out_1401321514683381355) {
   out_1401321514683381355[0] = 0;
   out_1401321514683381355[1] = 0;
   out_1401321514683381355[2] = 0;
   out_1401321514683381355[3] = 0;
   out_1401321514683381355[4] = 1;
   out_1401321514683381355[5] = 0;
   out_1401321514683381355[6] = 0;
   out_1401321514683381355[7] = 0;
   out_1401321514683381355[8] = 0;
   out_1401321514683381355[9] = 0;
   out_1401321514683381355[10] = 0;
   out_1401321514683381355[11] = 0;
   out_1401321514683381355[12] = 0;
   out_1401321514683381355[13] = 0;
   out_1401321514683381355[14] = 1;
   out_1401321514683381355[15] = 0;
   out_1401321514683381355[16] = 0;
   out_1401321514683381355[17] = 0;
}
void h_30(double *state, double *unused, double *out_5170903965876355224) {
   out_5170903965876355224[0] = state[4];
}
void H_30(double *state, double *unused, double *out_7244231945985549469) {
   out_7244231945985549469[0] = 0;
   out_7244231945985549469[1] = 0;
   out_7244231945985549469[2] = 0;
   out_7244231945985549469[3] = 0;
   out_7244231945985549469[4] = 1;
   out_7244231945985549469[5] = 0;
   out_7244231945985549469[6] = 0;
   out_7244231945985549469[7] = 0;
   out_7244231945985549469[8] = 0;
}
void h_26(double *state, double *unused, double *out_471825905204601611) {
   out_471825905204601611[0] = state[7];
}
void H_26(double *state, double *unused, double *out_3413961714380123510) {
   out_3413961714380123510[0] = 0;
   out_3413961714380123510[1] = 0;
   out_3413961714380123510[2] = 0;
   out_3413961714380123510[3] = 0;
   out_3413961714380123510[4] = 0;
   out_3413961714380123510[5] = 0;
   out_3413961714380123510[6] = 0;
   out_3413961714380123510[7] = 1;
   out_3413961714380123510[8] = 0;
}
void h_27(double *state, double *unused, double *out_8313805285979098383) {
   out_8313805285979098383[0] = state[3];
}
void H_27(double *state, double *unused, double *out_5069468634185124558) {
   out_5069468634185124558[0] = 0;
   out_5069468634185124558[1] = 0;
   out_5069468634185124558[2] = 0;
   out_5069468634185124558[3] = 1;
   out_5069468634185124558[4] = 0;
   out_5069468634185124558[5] = 0;
   out_5069468634185124558[6] = 0;
   out_5069468634185124558[7] = 0;
   out_5069468634185124558[8] = 0;
}
void h_29(double *state, double *unused, double *out_8274166840172350747) {
   out_8274166840172350747[0] = state[1];
}
void H_29(double *state, double *unused, double *out_3356105907315573525) {
   out_3356105907315573525[0] = 0;
   out_3356105907315573525[1] = 1;
   out_3356105907315573525[2] = 0;
   out_3356105907315573525[3] = 0;
   out_3356105907315573525[4] = 0;
   out_3356105907315573525[5] = 0;
   out_3356105907315573525[6] = 0;
   out_3356105907315573525[7] = 0;
   out_3356105907315573525[8] = 0;
}
void h_28(double *state, double *unused, double *out_2446841466723662246) {
   out_2446841466723662246[0] = state[0];
}
void H_28(double *state, double *unused, double *out_1726293109753957049) {
   out_1726293109753957049[0] = 1;
   out_1726293109753957049[1] = 0;
   out_1726293109753957049[2] = 0;
   out_1726293109753957049[3] = 0;
   out_1726293109753957049[4] = 0;
   out_1726293109753957049[5] = 0;
   out_1726293109753957049[6] = 0;
   out_1726293109753957049[7] = 0;
   out_1726293109753957049[8] = 0;
}
void h_31(double *state, double *unused, double *out_1259737292248810794) {
   out_1259737292248810794[0] = state[8];
}
void H_31(double *state, double *unused, double *out_358187566370893142) {
   out_358187566370893142[0] = 0;
   out_358187566370893142[1] = 0;
   out_358187566370893142[2] = 0;
   out_358187566370893142[3] = 0;
   out_358187566370893142[4] = 0;
   out_358187566370893142[5] = 0;
   out_358187566370893142[6] = 0;
   out_358187566370893142[7] = 0;
   out_358187566370893142[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_4652830232542905037) {
  err_fun(nom_x, delta_x, out_4652830232542905037);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_3291886134262608133) {
  inv_err_fun(nom_x, true_x, out_3291886134262608133);
}
void car_H_mod_fun(double *state, double *out_4576150220690732126) {
  H_mod_fun(state, out_4576150220690732126);
}
void car_f_fun(double *state, double dt, double *out_829378765985642412) {
  f_fun(state,  dt, out_829378765985642412);
}
void car_F_fun(double *state, double dt, double *out_5290468730257954652) {
  F_fun(state,  dt, out_5290468730257954652);
}
void car_h_25(double *state, double *unused, double *out_1533454437622332874) {
  h_25(state, unused, out_1533454437622332874);
}
void car_H_25(double *state, double *unused, double *out_327541604493932714) {
  H_25(state, unused, out_327541604493932714);
}
void car_h_24(double *state, double *unused, double *out_5835817958400148077) {
  h_24(state, unused, out_5835817958400148077);
}
void car_H_24(double *state, double *unused, double *out_1401321514683381355) {
  H_24(state, unused, out_1401321514683381355);
}
void car_h_30(double *state, double *unused, double *out_5170903965876355224) {
  h_30(state, unused, out_5170903965876355224);
}
void car_H_30(double *state, double *unused, double *out_7244231945985549469) {
  H_30(state, unused, out_7244231945985549469);
}
void car_h_26(double *state, double *unused, double *out_471825905204601611) {
  h_26(state, unused, out_471825905204601611);
}
void car_H_26(double *state, double *unused, double *out_3413961714380123510) {
  H_26(state, unused, out_3413961714380123510);
}
void car_h_27(double *state, double *unused, double *out_8313805285979098383) {
  h_27(state, unused, out_8313805285979098383);
}
void car_H_27(double *state, double *unused, double *out_5069468634185124558) {
  H_27(state, unused, out_5069468634185124558);
}
void car_h_29(double *state, double *unused, double *out_8274166840172350747) {
  h_29(state, unused, out_8274166840172350747);
}
void car_H_29(double *state, double *unused, double *out_3356105907315573525) {
  H_29(state, unused, out_3356105907315573525);
}
void car_h_28(double *state, double *unused, double *out_2446841466723662246) {
  h_28(state, unused, out_2446841466723662246);
}
void car_H_28(double *state, double *unused, double *out_1726293109753957049) {
  H_28(state, unused, out_1726293109753957049);
}
void car_h_31(double *state, double *unused, double *out_1259737292248810794) {
  h_31(state, unused, out_1259737292248810794);
}
void car_H_31(double *state, double *unused, double *out_358187566370893142) {
  H_31(state, unused, out_358187566370893142);
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
