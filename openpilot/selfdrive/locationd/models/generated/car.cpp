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
void err_fun(double *nom_x, double *delta_x, double *out_505673110852134299) {
   out_505673110852134299[0] = delta_x[0] + nom_x[0];
   out_505673110852134299[1] = delta_x[1] + nom_x[1];
   out_505673110852134299[2] = delta_x[2] + nom_x[2];
   out_505673110852134299[3] = delta_x[3] + nom_x[3];
   out_505673110852134299[4] = delta_x[4] + nom_x[4];
   out_505673110852134299[5] = delta_x[5] + nom_x[5];
   out_505673110852134299[6] = delta_x[6] + nom_x[6];
   out_505673110852134299[7] = delta_x[7] + nom_x[7];
   out_505673110852134299[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_6882414693674412674) {
   out_6882414693674412674[0] = -nom_x[0] + true_x[0];
   out_6882414693674412674[1] = -nom_x[1] + true_x[1];
   out_6882414693674412674[2] = -nom_x[2] + true_x[2];
   out_6882414693674412674[3] = -nom_x[3] + true_x[3];
   out_6882414693674412674[4] = -nom_x[4] + true_x[4];
   out_6882414693674412674[5] = -nom_x[5] + true_x[5];
   out_6882414693674412674[6] = -nom_x[6] + true_x[6];
   out_6882414693674412674[7] = -nom_x[7] + true_x[7];
   out_6882414693674412674[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_7704283056742914524) {
   out_7704283056742914524[0] = 1.0;
   out_7704283056742914524[1] = 0.0;
   out_7704283056742914524[2] = 0.0;
   out_7704283056742914524[3] = 0.0;
   out_7704283056742914524[4] = 0.0;
   out_7704283056742914524[5] = 0.0;
   out_7704283056742914524[6] = 0.0;
   out_7704283056742914524[7] = 0.0;
   out_7704283056742914524[8] = 0.0;
   out_7704283056742914524[9] = 0.0;
   out_7704283056742914524[10] = 1.0;
   out_7704283056742914524[11] = 0.0;
   out_7704283056742914524[12] = 0.0;
   out_7704283056742914524[13] = 0.0;
   out_7704283056742914524[14] = 0.0;
   out_7704283056742914524[15] = 0.0;
   out_7704283056742914524[16] = 0.0;
   out_7704283056742914524[17] = 0.0;
   out_7704283056742914524[18] = 0.0;
   out_7704283056742914524[19] = 0.0;
   out_7704283056742914524[20] = 1.0;
   out_7704283056742914524[21] = 0.0;
   out_7704283056742914524[22] = 0.0;
   out_7704283056742914524[23] = 0.0;
   out_7704283056742914524[24] = 0.0;
   out_7704283056742914524[25] = 0.0;
   out_7704283056742914524[26] = 0.0;
   out_7704283056742914524[27] = 0.0;
   out_7704283056742914524[28] = 0.0;
   out_7704283056742914524[29] = 0.0;
   out_7704283056742914524[30] = 1.0;
   out_7704283056742914524[31] = 0.0;
   out_7704283056742914524[32] = 0.0;
   out_7704283056742914524[33] = 0.0;
   out_7704283056742914524[34] = 0.0;
   out_7704283056742914524[35] = 0.0;
   out_7704283056742914524[36] = 0.0;
   out_7704283056742914524[37] = 0.0;
   out_7704283056742914524[38] = 0.0;
   out_7704283056742914524[39] = 0.0;
   out_7704283056742914524[40] = 1.0;
   out_7704283056742914524[41] = 0.0;
   out_7704283056742914524[42] = 0.0;
   out_7704283056742914524[43] = 0.0;
   out_7704283056742914524[44] = 0.0;
   out_7704283056742914524[45] = 0.0;
   out_7704283056742914524[46] = 0.0;
   out_7704283056742914524[47] = 0.0;
   out_7704283056742914524[48] = 0.0;
   out_7704283056742914524[49] = 0.0;
   out_7704283056742914524[50] = 1.0;
   out_7704283056742914524[51] = 0.0;
   out_7704283056742914524[52] = 0.0;
   out_7704283056742914524[53] = 0.0;
   out_7704283056742914524[54] = 0.0;
   out_7704283056742914524[55] = 0.0;
   out_7704283056742914524[56] = 0.0;
   out_7704283056742914524[57] = 0.0;
   out_7704283056742914524[58] = 0.0;
   out_7704283056742914524[59] = 0.0;
   out_7704283056742914524[60] = 1.0;
   out_7704283056742914524[61] = 0.0;
   out_7704283056742914524[62] = 0.0;
   out_7704283056742914524[63] = 0.0;
   out_7704283056742914524[64] = 0.0;
   out_7704283056742914524[65] = 0.0;
   out_7704283056742914524[66] = 0.0;
   out_7704283056742914524[67] = 0.0;
   out_7704283056742914524[68] = 0.0;
   out_7704283056742914524[69] = 0.0;
   out_7704283056742914524[70] = 1.0;
   out_7704283056742914524[71] = 0.0;
   out_7704283056742914524[72] = 0.0;
   out_7704283056742914524[73] = 0.0;
   out_7704283056742914524[74] = 0.0;
   out_7704283056742914524[75] = 0.0;
   out_7704283056742914524[76] = 0.0;
   out_7704283056742914524[77] = 0.0;
   out_7704283056742914524[78] = 0.0;
   out_7704283056742914524[79] = 0.0;
   out_7704283056742914524[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_805026565951573056) {
   out_805026565951573056[0] = state[0];
   out_805026565951573056[1] = state[1];
   out_805026565951573056[2] = state[2];
   out_805026565951573056[3] = state[3];
   out_805026565951573056[4] = state[4];
   out_805026565951573056[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_805026565951573056[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_805026565951573056[7] = state[7];
   out_805026565951573056[8] = state[8];
}
void F_fun(double *state, double dt, double *out_4749317775827675729) {
   out_4749317775827675729[0] = 1;
   out_4749317775827675729[1] = 0;
   out_4749317775827675729[2] = 0;
   out_4749317775827675729[3] = 0;
   out_4749317775827675729[4] = 0;
   out_4749317775827675729[5] = 0;
   out_4749317775827675729[6] = 0;
   out_4749317775827675729[7] = 0;
   out_4749317775827675729[8] = 0;
   out_4749317775827675729[9] = 0;
   out_4749317775827675729[10] = 1;
   out_4749317775827675729[11] = 0;
   out_4749317775827675729[12] = 0;
   out_4749317775827675729[13] = 0;
   out_4749317775827675729[14] = 0;
   out_4749317775827675729[15] = 0;
   out_4749317775827675729[16] = 0;
   out_4749317775827675729[17] = 0;
   out_4749317775827675729[18] = 0;
   out_4749317775827675729[19] = 0;
   out_4749317775827675729[20] = 1;
   out_4749317775827675729[21] = 0;
   out_4749317775827675729[22] = 0;
   out_4749317775827675729[23] = 0;
   out_4749317775827675729[24] = 0;
   out_4749317775827675729[25] = 0;
   out_4749317775827675729[26] = 0;
   out_4749317775827675729[27] = 0;
   out_4749317775827675729[28] = 0;
   out_4749317775827675729[29] = 0;
   out_4749317775827675729[30] = 1;
   out_4749317775827675729[31] = 0;
   out_4749317775827675729[32] = 0;
   out_4749317775827675729[33] = 0;
   out_4749317775827675729[34] = 0;
   out_4749317775827675729[35] = 0;
   out_4749317775827675729[36] = 0;
   out_4749317775827675729[37] = 0;
   out_4749317775827675729[38] = 0;
   out_4749317775827675729[39] = 0;
   out_4749317775827675729[40] = 1;
   out_4749317775827675729[41] = 0;
   out_4749317775827675729[42] = 0;
   out_4749317775827675729[43] = 0;
   out_4749317775827675729[44] = 0;
   out_4749317775827675729[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_4749317775827675729[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_4749317775827675729[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_4749317775827675729[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_4749317775827675729[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_4749317775827675729[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_4749317775827675729[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_4749317775827675729[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_4749317775827675729[53] = -9.8100000000000005*dt;
   out_4749317775827675729[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_4749317775827675729[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_4749317775827675729[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_4749317775827675729[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_4749317775827675729[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_4749317775827675729[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_4749317775827675729[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_4749317775827675729[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_4749317775827675729[62] = 0;
   out_4749317775827675729[63] = 0;
   out_4749317775827675729[64] = 0;
   out_4749317775827675729[65] = 0;
   out_4749317775827675729[66] = 0;
   out_4749317775827675729[67] = 0;
   out_4749317775827675729[68] = 0;
   out_4749317775827675729[69] = 0;
   out_4749317775827675729[70] = 1;
   out_4749317775827675729[71] = 0;
   out_4749317775827675729[72] = 0;
   out_4749317775827675729[73] = 0;
   out_4749317775827675729[74] = 0;
   out_4749317775827675729[75] = 0;
   out_4749317775827675729[76] = 0;
   out_4749317775827675729[77] = 0;
   out_4749317775827675729[78] = 0;
   out_4749317775827675729[79] = 0;
   out_4749317775827675729[80] = 1;
}
void h_25(double *state, double *unused, double *out_5457839146770041094) {
   out_5457839146770041094[0] = state[6];
}
void H_25(double *state, double *unused, double *out_8041768441628026604) {
   out_8041768441628026604[0] = 0;
   out_8041768441628026604[1] = 0;
   out_8041768441628026604[2] = 0;
   out_8041768441628026604[3] = 0;
   out_8041768441628026604[4] = 0;
   out_8041768441628026604[5] = 0;
   out_8041768441628026604[6] = 1;
   out_8041768441628026604[7] = 0;
   out_8041768441628026604[8] = 0;
}
void h_24(double *state, double *unused, double *out_7008468248151095265) {
   out_7008468248151095265[0] = state[4];
   out_7008468248151095265[1] = state[5];
}
void H_24(double *state, double *unused, double *out_623376807951099711) {
   out_623376807951099711[0] = 0;
   out_623376807951099711[1] = 0;
   out_623376807951099711[2] = 0;
   out_623376807951099711[3] = 0;
   out_623376807951099711[4] = 1;
   out_623376807951099711[5] = 0;
   out_623376807951099711[6] = 0;
   out_623376807951099711[7] = 0;
   out_623376807951099711[8] = 0;
   out_623376807951099711[9] = 0;
   out_623376807951099711[10] = 0;
   out_623376807951099711[11] = 0;
   out_623376807951099711[12] = 0;
   out_623376807951099711[13] = 0;
   out_623376807951099711[14] = 1;
   out_623376807951099711[15] = 0;
   out_623376807951099711[16] = 0;
   out_623376807951099711[17] = 0;
}
void h_30(double *state, double *unused, double *out_4076126567568063137) {
   out_4076126567568063137[0] = state[4];
}
void H_30(double *state, double *unused, double *out_8171107388771266674) {
   out_8171107388771266674[0] = 0;
   out_8171107388771266674[1] = 0;
   out_8171107388771266674[2] = 0;
   out_8171107388771266674[3] = 0;
   out_8171107388771266674[4] = 1;
   out_8171107388771266674[5] = 0;
   out_8171107388771266674[6] = 0;
   out_8171107388771266674[7] = 0;
   out_8171107388771266674[8] = 0;
}
void h_26(double *state, double *unused, double *out_5964960686497261826) {
   out_5964960686497261826[0] = state[7];
}
void H_26(double *state, double *unused, double *out_6663472313207468788) {
   out_6663472313207468788[0] = 0;
   out_6663472313207468788[1] = 0;
   out_6663472313207468788[2] = 0;
   out_6663472313207468788[3] = 0;
   out_6663472313207468788[4] = 0;
   out_6663472313207468788[5] = 0;
   out_6663472313207468788[6] = 0;
   out_6663472313207468788[7] = 1;
   out_6663472313207468788[8] = 0;
}
void h_27(double *state, double *unused, double *out_5553761492510809709) {
   out_5553761492510809709[0] = state[3];
}
void H_27(double *state, double *unused, double *out_8100873373137860031) {
   out_8100873373137860031[0] = 0;
   out_8100873373137860031[1] = 0;
   out_8100873373137860031[2] = 0;
   out_8100873373137860031[3] = 1;
   out_8100873373137860031[4] = 0;
   out_8100873373137860031[5] = 0;
   out_8100873373137860031[6] = 0;
   out_8100873373137860031[7] = 0;
   out_8100873373137860031[8] = 0;
}
void h_29(double *state, double *unused, double *out_1906797271738078616) {
   out_1906797271738078616[0] = state[1];
}
void H_29(double *state, double *unused, double *out_6387510646268308998) {
   out_6387510646268308998[0] = 0;
   out_6387510646268308998[1] = 1;
   out_6387510646268308998[2] = 0;
   out_6387510646268308998[3] = 0;
   out_6387510646268308998[4] = 0;
   out_6387510646268308998[5] = 0;
   out_6387510646268308998[6] = 0;
   out_6387510646268308998[7] = 0;
   out_6387510646268308998[8] = 0;
}
void h_28(double *state, double *unused, double *out_4194133961501439881) {
   out_4194133961501439881[0] = state[0];
}
void H_28(double *state, double *unused, double *out_8351140917833635249) {
   out_8351140917833635249[0] = 1;
   out_8351140917833635249[1] = 0;
   out_8351140917833635249[2] = 0;
   out_8351140917833635249[3] = 0;
   out_8351140917833635249[4] = 0;
   out_8351140917833635249[5] = 0;
   out_8351140917833635249[6] = 0;
   out_8351140917833635249[7] = 0;
   out_8351140917833635249[8] = 0;
}
void h_31(double *state, double *unused, double *out_1312996079580309842) {
   out_1312996079580309842[0] = state[8];
}
void H_31(double *state, double *unused, double *out_8011122479751066176) {
   out_8011122479751066176[0] = 0;
   out_8011122479751066176[1] = 0;
   out_8011122479751066176[2] = 0;
   out_8011122479751066176[3] = 0;
   out_8011122479751066176[4] = 0;
   out_8011122479751066176[5] = 0;
   out_8011122479751066176[6] = 0;
   out_8011122479751066176[7] = 0;
   out_8011122479751066176[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_505673110852134299) {
  err_fun(nom_x, delta_x, out_505673110852134299);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_6882414693674412674) {
  inv_err_fun(nom_x, true_x, out_6882414693674412674);
}
void car_H_mod_fun(double *state, double *out_7704283056742914524) {
  H_mod_fun(state, out_7704283056742914524);
}
void car_f_fun(double *state, double dt, double *out_805026565951573056) {
  f_fun(state,  dt, out_805026565951573056);
}
void car_F_fun(double *state, double dt, double *out_4749317775827675729) {
  F_fun(state,  dt, out_4749317775827675729);
}
void car_h_25(double *state, double *unused, double *out_5457839146770041094) {
  h_25(state, unused, out_5457839146770041094);
}
void car_H_25(double *state, double *unused, double *out_8041768441628026604) {
  H_25(state, unused, out_8041768441628026604);
}
void car_h_24(double *state, double *unused, double *out_7008468248151095265) {
  h_24(state, unused, out_7008468248151095265);
}
void car_H_24(double *state, double *unused, double *out_623376807951099711) {
  H_24(state, unused, out_623376807951099711);
}
void car_h_30(double *state, double *unused, double *out_4076126567568063137) {
  h_30(state, unused, out_4076126567568063137);
}
void car_H_30(double *state, double *unused, double *out_8171107388771266674) {
  H_30(state, unused, out_8171107388771266674);
}
void car_h_26(double *state, double *unused, double *out_5964960686497261826) {
  h_26(state, unused, out_5964960686497261826);
}
void car_H_26(double *state, double *unused, double *out_6663472313207468788) {
  H_26(state, unused, out_6663472313207468788);
}
void car_h_27(double *state, double *unused, double *out_5553761492510809709) {
  h_27(state, unused, out_5553761492510809709);
}
void car_H_27(double *state, double *unused, double *out_8100873373137860031) {
  H_27(state, unused, out_8100873373137860031);
}
void car_h_29(double *state, double *unused, double *out_1906797271738078616) {
  h_29(state, unused, out_1906797271738078616);
}
void car_H_29(double *state, double *unused, double *out_6387510646268308998) {
  H_29(state, unused, out_6387510646268308998);
}
void car_h_28(double *state, double *unused, double *out_4194133961501439881) {
  h_28(state, unused, out_4194133961501439881);
}
void car_H_28(double *state, double *unused, double *out_8351140917833635249) {
  H_28(state, unused, out_8351140917833635249);
}
void car_h_31(double *state, double *unused, double *out_1312996079580309842) {
  h_31(state, unused, out_1312996079580309842);
}
void car_H_31(double *state, double *unused, double *out_8011122479751066176) {
  H_31(state, unused, out_8011122479751066176);
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
