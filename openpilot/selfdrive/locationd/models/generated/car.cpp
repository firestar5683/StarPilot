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
void err_fun(double *nom_x, double *delta_x, double *out_408914854931955974) {
   out_408914854931955974[0] = delta_x[0] + nom_x[0];
   out_408914854931955974[1] = delta_x[1] + nom_x[1];
   out_408914854931955974[2] = delta_x[2] + nom_x[2];
   out_408914854931955974[3] = delta_x[3] + nom_x[3];
   out_408914854931955974[4] = delta_x[4] + nom_x[4];
   out_408914854931955974[5] = delta_x[5] + nom_x[5];
   out_408914854931955974[6] = delta_x[6] + nom_x[6];
   out_408914854931955974[7] = delta_x[7] + nom_x[7];
   out_408914854931955974[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_177131998479136517) {
   out_177131998479136517[0] = -nom_x[0] + true_x[0];
   out_177131998479136517[1] = -nom_x[1] + true_x[1];
   out_177131998479136517[2] = -nom_x[2] + true_x[2];
   out_177131998479136517[3] = -nom_x[3] + true_x[3];
   out_177131998479136517[4] = -nom_x[4] + true_x[4];
   out_177131998479136517[5] = -nom_x[5] + true_x[5];
   out_177131998479136517[6] = -nom_x[6] + true_x[6];
   out_177131998479136517[7] = -nom_x[7] + true_x[7];
   out_177131998479136517[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_612188567970168411) {
   out_612188567970168411[0] = 1.0;
   out_612188567970168411[1] = 0.0;
   out_612188567970168411[2] = 0.0;
   out_612188567970168411[3] = 0.0;
   out_612188567970168411[4] = 0.0;
   out_612188567970168411[5] = 0.0;
   out_612188567970168411[6] = 0.0;
   out_612188567970168411[7] = 0.0;
   out_612188567970168411[8] = 0.0;
   out_612188567970168411[9] = 0.0;
   out_612188567970168411[10] = 1.0;
   out_612188567970168411[11] = 0.0;
   out_612188567970168411[12] = 0.0;
   out_612188567970168411[13] = 0.0;
   out_612188567970168411[14] = 0.0;
   out_612188567970168411[15] = 0.0;
   out_612188567970168411[16] = 0.0;
   out_612188567970168411[17] = 0.0;
   out_612188567970168411[18] = 0.0;
   out_612188567970168411[19] = 0.0;
   out_612188567970168411[20] = 1.0;
   out_612188567970168411[21] = 0.0;
   out_612188567970168411[22] = 0.0;
   out_612188567970168411[23] = 0.0;
   out_612188567970168411[24] = 0.0;
   out_612188567970168411[25] = 0.0;
   out_612188567970168411[26] = 0.0;
   out_612188567970168411[27] = 0.0;
   out_612188567970168411[28] = 0.0;
   out_612188567970168411[29] = 0.0;
   out_612188567970168411[30] = 1.0;
   out_612188567970168411[31] = 0.0;
   out_612188567970168411[32] = 0.0;
   out_612188567970168411[33] = 0.0;
   out_612188567970168411[34] = 0.0;
   out_612188567970168411[35] = 0.0;
   out_612188567970168411[36] = 0.0;
   out_612188567970168411[37] = 0.0;
   out_612188567970168411[38] = 0.0;
   out_612188567970168411[39] = 0.0;
   out_612188567970168411[40] = 1.0;
   out_612188567970168411[41] = 0.0;
   out_612188567970168411[42] = 0.0;
   out_612188567970168411[43] = 0.0;
   out_612188567970168411[44] = 0.0;
   out_612188567970168411[45] = 0.0;
   out_612188567970168411[46] = 0.0;
   out_612188567970168411[47] = 0.0;
   out_612188567970168411[48] = 0.0;
   out_612188567970168411[49] = 0.0;
   out_612188567970168411[50] = 1.0;
   out_612188567970168411[51] = 0.0;
   out_612188567970168411[52] = 0.0;
   out_612188567970168411[53] = 0.0;
   out_612188567970168411[54] = 0.0;
   out_612188567970168411[55] = 0.0;
   out_612188567970168411[56] = 0.0;
   out_612188567970168411[57] = 0.0;
   out_612188567970168411[58] = 0.0;
   out_612188567970168411[59] = 0.0;
   out_612188567970168411[60] = 1.0;
   out_612188567970168411[61] = 0.0;
   out_612188567970168411[62] = 0.0;
   out_612188567970168411[63] = 0.0;
   out_612188567970168411[64] = 0.0;
   out_612188567970168411[65] = 0.0;
   out_612188567970168411[66] = 0.0;
   out_612188567970168411[67] = 0.0;
   out_612188567970168411[68] = 0.0;
   out_612188567970168411[69] = 0.0;
   out_612188567970168411[70] = 1.0;
   out_612188567970168411[71] = 0.0;
   out_612188567970168411[72] = 0.0;
   out_612188567970168411[73] = 0.0;
   out_612188567970168411[74] = 0.0;
   out_612188567970168411[75] = 0.0;
   out_612188567970168411[76] = 0.0;
   out_612188567970168411[77] = 0.0;
   out_612188567970168411[78] = 0.0;
   out_612188567970168411[79] = 0.0;
   out_612188567970168411[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_1999864885543950499) {
   out_1999864885543950499[0] = state[0];
   out_1999864885543950499[1] = state[1];
   out_1999864885543950499[2] = state[2];
   out_1999864885543950499[3] = state[3];
   out_1999864885543950499[4] = state[4];
   out_1999864885543950499[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_1999864885543950499[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_1999864885543950499[7] = state[7];
   out_1999864885543950499[8] = state[8];
}
void F_fun(double *state, double dt, double *out_3889473353313594997) {
   out_3889473353313594997[0] = 1;
   out_3889473353313594997[1] = 0;
   out_3889473353313594997[2] = 0;
   out_3889473353313594997[3] = 0;
   out_3889473353313594997[4] = 0;
   out_3889473353313594997[5] = 0;
   out_3889473353313594997[6] = 0;
   out_3889473353313594997[7] = 0;
   out_3889473353313594997[8] = 0;
   out_3889473353313594997[9] = 0;
   out_3889473353313594997[10] = 1;
   out_3889473353313594997[11] = 0;
   out_3889473353313594997[12] = 0;
   out_3889473353313594997[13] = 0;
   out_3889473353313594997[14] = 0;
   out_3889473353313594997[15] = 0;
   out_3889473353313594997[16] = 0;
   out_3889473353313594997[17] = 0;
   out_3889473353313594997[18] = 0;
   out_3889473353313594997[19] = 0;
   out_3889473353313594997[20] = 1;
   out_3889473353313594997[21] = 0;
   out_3889473353313594997[22] = 0;
   out_3889473353313594997[23] = 0;
   out_3889473353313594997[24] = 0;
   out_3889473353313594997[25] = 0;
   out_3889473353313594997[26] = 0;
   out_3889473353313594997[27] = 0;
   out_3889473353313594997[28] = 0;
   out_3889473353313594997[29] = 0;
   out_3889473353313594997[30] = 1;
   out_3889473353313594997[31] = 0;
   out_3889473353313594997[32] = 0;
   out_3889473353313594997[33] = 0;
   out_3889473353313594997[34] = 0;
   out_3889473353313594997[35] = 0;
   out_3889473353313594997[36] = 0;
   out_3889473353313594997[37] = 0;
   out_3889473353313594997[38] = 0;
   out_3889473353313594997[39] = 0;
   out_3889473353313594997[40] = 1;
   out_3889473353313594997[41] = 0;
   out_3889473353313594997[42] = 0;
   out_3889473353313594997[43] = 0;
   out_3889473353313594997[44] = 0;
   out_3889473353313594997[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_3889473353313594997[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_3889473353313594997[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_3889473353313594997[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_3889473353313594997[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_3889473353313594997[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_3889473353313594997[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_3889473353313594997[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_3889473353313594997[53] = -9.8100000000000005*dt;
   out_3889473353313594997[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_3889473353313594997[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_3889473353313594997[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_3889473353313594997[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_3889473353313594997[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_3889473353313594997[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_3889473353313594997[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_3889473353313594997[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_3889473353313594997[62] = 0;
   out_3889473353313594997[63] = 0;
   out_3889473353313594997[64] = 0;
   out_3889473353313594997[65] = 0;
   out_3889473353313594997[66] = 0;
   out_3889473353313594997[67] = 0;
   out_3889473353313594997[68] = 0;
   out_3889473353313594997[69] = 0;
   out_3889473353313594997[70] = 1;
   out_3889473353313594997[71] = 0;
   out_3889473353313594997[72] = 0;
   out_3889473353313594997[73] = 0;
   out_3889473353313594997[74] = 0;
   out_3889473353313594997[75] = 0;
   out_3889473353313594997[76] = 0;
   out_3889473353313594997[77] = 0;
   out_3889473353313594997[78] = 0;
   out_3889473353313594997[79] = 0;
   out_3889473353313594997[80] = 1;
}
void h_25(double *state, double *unused, double *out_4691870608107024689) {
   out_4691870608107024689[0] = state[6];
}
void H_25(double *state, double *unused, double *out_4135237206615533559) {
   out_4135237206615533559[0] = 0;
   out_4135237206615533559[1] = 0;
   out_4135237206615533559[2] = 0;
   out_4135237206615533559[3] = 0;
   out_4135237206615533559[4] = 0;
   out_4135237206615533559[5] = 0;
   out_4135237206615533559[6] = 1;
   out_4135237206615533559[7] = 0;
   out_4135237206615533559[8] = 0;
}
void h_24(double *state, double *unused, double *out_7256933575834984536) {
   out_7256933575834984536[0] = state[4];
   out_7256933575834984536[1] = state[5];
}
void H_24(double *state, double *unused, double *out_3151171335774219891) {
   out_3151171335774219891[0] = 0;
   out_3151171335774219891[1] = 0;
   out_3151171335774219891[2] = 0;
   out_3151171335774219891[3] = 0;
   out_3151171335774219891[4] = 1;
   out_3151171335774219891[5] = 0;
   out_3151171335774219891[6] = 0;
   out_3151171335774219891[7] = 0;
   out_3151171335774219891[8] = 0;
   out_3151171335774219891[9] = 0;
   out_3151171335774219891[10] = 0;
   out_3151171335774219891[11] = 0;
   out_3151171335774219891[12] = 0;
   out_3151171335774219891[13] = 0;
   out_3151171335774219891[14] = 1;
   out_3151171335774219891[15] = 0;
   out_3151171335774219891[16] = 0;
   out_3151171335774219891[17] = 0;
}
void h_30(double *state, double *unused, double *out_6984038239252175991) {
   out_6984038239252175991[0] = state[4];
}
void H_30(double *state, double *unused, double *out_2781453134876083196) {
   out_2781453134876083196[0] = 0;
   out_2781453134876083196[1] = 0;
   out_2781453134876083196[2] = 0;
   out_2781453134876083196[3] = 0;
   out_2781453134876083196[4] = 1;
   out_2781453134876083196[5] = 0;
   out_2781453134876083196[6] = 0;
   out_2781453134876083196[7] = 0;
   out_2781453134876083196[8] = 0;
}
void h_26(double *state, double *unused, double *out_8151782040328317728) {
   out_8151782040328317728[0] = state[7];
}
void H_26(double *state, double *unused, double *out_830711236854732958) {
   out_830711236854732958[0] = 0;
   out_830711236854732958[1] = 0;
   out_830711236854732958[2] = 0;
   out_830711236854732958[3] = 0;
   out_830711236854732958[4] = 0;
   out_830711236854732958[5] = 0;
   out_830711236854732958[6] = 0;
   out_830711236854732958[7] = 1;
   out_830711236854732958[8] = 0;
}
void h_27(double *state, double *unused, double *out_6382318442842705649) {
   out_6382318442842705649[0] = state[3];
}
void H_27(double *state, double *unused, double *out_606689823075658285) {
   out_606689823075658285[0] = 0;
   out_606689823075658285[1] = 0;
   out_606689823075658285[2] = 0;
   out_606689823075658285[3] = 1;
   out_606689823075658285[4] = 0;
   out_606689823075658285[5] = 0;
   out_606689823075658285[6] = 0;
   out_606689823075658285[7] = 0;
   out_606689823075658285[8] = 0;
}
void h_29(double *state, double *unused, double *out_205509483633589514) {
   out_205509483633589514[0] = state[1];
}
void H_29(double *state, double *unused, double *out_3291684479190475380) {
   out_3291684479190475380[0] = 0;
   out_3291684479190475380[1] = 1;
   out_3291684479190475380[2] = 0;
   out_3291684479190475380[3] = 0;
   out_3291684479190475380[4] = 0;
   out_3291684479190475380[5] = 0;
   out_3291684479190475380[6] = 0;
   out_3291684479190475380[7] = 0;
   out_3291684479190475380[8] = 0;
}
void h_28(double *state, double *unused, double *out_1380645175181860004) {
   out_1380645175181860004[0] = state[0];
}
void H_28(double *state, double *unused, double *out_1790714537879055194) {
   out_1790714537879055194[0] = 1;
   out_1790714537879055194[1] = 0;
   out_1790714537879055194[2] = 0;
   out_1790714537879055194[3] = 0;
   out_1790714537879055194[4] = 0;
   out_1790714537879055194[5] = 0;
   out_1790714537879055194[6] = 0;
   out_1790714537879055194[7] = 0;
   out_1790714537879055194[8] = 0;
}
void h_31(double *state, double *unused, double *out_4534683939755895544) {
   out_4534683939755895544[0] = state[8];
}
void H_31(double *state, double *unused, double *out_4104591244738573131) {
   out_4104591244738573131[0] = 0;
   out_4104591244738573131[1] = 0;
   out_4104591244738573131[2] = 0;
   out_4104591244738573131[3] = 0;
   out_4104591244738573131[4] = 0;
   out_4104591244738573131[5] = 0;
   out_4104591244738573131[6] = 0;
   out_4104591244738573131[7] = 0;
   out_4104591244738573131[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_408914854931955974) {
  err_fun(nom_x, delta_x, out_408914854931955974);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_177131998479136517) {
  inv_err_fun(nom_x, true_x, out_177131998479136517);
}
void car_H_mod_fun(double *state, double *out_612188567970168411) {
  H_mod_fun(state, out_612188567970168411);
}
void car_f_fun(double *state, double dt, double *out_1999864885543950499) {
  f_fun(state,  dt, out_1999864885543950499);
}
void car_F_fun(double *state, double dt, double *out_3889473353313594997) {
  F_fun(state,  dt, out_3889473353313594997);
}
void car_h_25(double *state, double *unused, double *out_4691870608107024689) {
  h_25(state, unused, out_4691870608107024689);
}
void car_H_25(double *state, double *unused, double *out_4135237206615533559) {
  H_25(state, unused, out_4135237206615533559);
}
void car_h_24(double *state, double *unused, double *out_7256933575834984536) {
  h_24(state, unused, out_7256933575834984536);
}
void car_H_24(double *state, double *unused, double *out_3151171335774219891) {
  H_24(state, unused, out_3151171335774219891);
}
void car_h_30(double *state, double *unused, double *out_6984038239252175991) {
  h_30(state, unused, out_6984038239252175991);
}
void car_H_30(double *state, double *unused, double *out_2781453134876083196) {
  H_30(state, unused, out_2781453134876083196);
}
void car_h_26(double *state, double *unused, double *out_8151782040328317728) {
  h_26(state, unused, out_8151782040328317728);
}
void car_H_26(double *state, double *unused, double *out_830711236854732958) {
  H_26(state, unused, out_830711236854732958);
}
void car_h_27(double *state, double *unused, double *out_6382318442842705649) {
  h_27(state, unused, out_6382318442842705649);
}
void car_H_27(double *state, double *unused, double *out_606689823075658285) {
  H_27(state, unused, out_606689823075658285);
}
void car_h_29(double *state, double *unused, double *out_205509483633589514) {
  h_29(state, unused, out_205509483633589514);
}
void car_H_29(double *state, double *unused, double *out_3291684479190475380) {
  H_29(state, unused, out_3291684479190475380);
}
void car_h_28(double *state, double *unused, double *out_1380645175181860004) {
  h_28(state, unused, out_1380645175181860004);
}
void car_H_28(double *state, double *unused, double *out_1790714537879055194) {
  H_28(state, unused, out_1790714537879055194);
}
void car_h_31(double *state, double *unused, double *out_4534683939755895544) {
  h_31(state, unused, out_4534683939755895544);
}
void car_H_31(double *state, double *unused, double *out_4104591244738573131) {
  H_31(state, unused, out_4104591244738573131);
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
