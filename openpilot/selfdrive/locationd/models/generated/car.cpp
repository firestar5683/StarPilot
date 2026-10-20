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
void err_fun(double *nom_x, double *delta_x, double *out_4191231468621882354) {
   out_4191231468621882354[0] = delta_x[0] + nom_x[0];
   out_4191231468621882354[1] = delta_x[1] + nom_x[1];
   out_4191231468621882354[2] = delta_x[2] + nom_x[2];
   out_4191231468621882354[3] = delta_x[3] + nom_x[3];
   out_4191231468621882354[4] = delta_x[4] + nom_x[4];
   out_4191231468621882354[5] = delta_x[5] + nom_x[5];
   out_4191231468621882354[6] = delta_x[6] + nom_x[6];
   out_4191231468621882354[7] = delta_x[7] + nom_x[7];
   out_4191231468621882354[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_4409511713992133464) {
   out_4409511713992133464[0] = -nom_x[0] + true_x[0];
   out_4409511713992133464[1] = -nom_x[1] + true_x[1];
   out_4409511713992133464[2] = -nom_x[2] + true_x[2];
   out_4409511713992133464[3] = -nom_x[3] + true_x[3];
   out_4409511713992133464[4] = -nom_x[4] + true_x[4];
   out_4409511713992133464[5] = -nom_x[5] + true_x[5];
   out_4409511713992133464[6] = -nom_x[6] + true_x[6];
   out_4409511713992133464[7] = -nom_x[7] + true_x[7];
   out_4409511713992133464[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_7704822479144562897) {
   out_7704822479144562897[0] = 1.0;
   out_7704822479144562897[1] = 0.0;
   out_7704822479144562897[2] = 0.0;
   out_7704822479144562897[3] = 0.0;
   out_7704822479144562897[4] = 0.0;
   out_7704822479144562897[5] = 0.0;
   out_7704822479144562897[6] = 0.0;
   out_7704822479144562897[7] = 0.0;
   out_7704822479144562897[8] = 0.0;
   out_7704822479144562897[9] = 0.0;
   out_7704822479144562897[10] = 1.0;
   out_7704822479144562897[11] = 0.0;
   out_7704822479144562897[12] = 0.0;
   out_7704822479144562897[13] = 0.0;
   out_7704822479144562897[14] = 0.0;
   out_7704822479144562897[15] = 0.0;
   out_7704822479144562897[16] = 0.0;
   out_7704822479144562897[17] = 0.0;
   out_7704822479144562897[18] = 0.0;
   out_7704822479144562897[19] = 0.0;
   out_7704822479144562897[20] = 1.0;
   out_7704822479144562897[21] = 0.0;
   out_7704822479144562897[22] = 0.0;
   out_7704822479144562897[23] = 0.0;
   out_7704822479144562897[24] = 0.0;
   out_7704822479144562897[25] = 0.0;
   out_7704822479144562897[26] = 0.0;
   out_7704822479144562897[27] = 0.0;
   out_7704822479144562897[28] = 0.0;
   out_7704822479144562897[29] = 0.0;
   out_7704822479144562897[30] = 1.0;
   out_7704822479144562897[31] = 0.0;
   out_7704822479144562897[32] = 0.0;
   out_7704822479144562897[33] = 0.0;
   out_7704822479144562897[34] = 0.0;
   out_7704822479144562897[35] = 0.0;
   out_7704822479144562897[36] = 0.0;
   out_7704822479144562897[37] = 0.0;
   out_7704822479144562897[38] = 0.0;
   out_7704822479144562897[39] = 0.0;
   out_7704822479144562897[40] = 1.0;
   out_7704822479144562897[41] = 0.0;
   out_7704822479144562897[42] = 0.0;
   out_7704822479144562897[43] = 0.0;
   out_7704822479144562897[44] = 0.0;
   out_7704822479144562897[45] = 0.0;
   out_7704822479144562897[46] = 0.0;
   out_7704822479144562897[47] = 0.0;
   out_7704822479144562897[48] = 0.0;
   out_7704822479144562897[49] = 0.0;
   out_7704822479144562897[50] = 1.0;
   out_7704822479144562897[51] = 0.0;
   out_7704822479144562897[52] = 0.0;
   out_7704822479144562897[53] = 0.0;
   out_7704822479144562897[54] = 0.0;
   out_7704822479144562897[55] = 0.0;
   out_7704822479144562897[56] = 0.0;
   out_7704822479144562897[57] = 0.0;
   out_7704822479144562897[58] = 0.0;
   out_7704822479144562897[59] = 0.0;
   out_7704822479144562897[60] = 1.0;
   out_7704822479144562897[61] = 0.0;
   out_7704822479144562897[62] = 0.0;
   out_7704822479144562897[63] = 0.0;
   out_7704822479144562897[64] = 0.0;
   out_7704822479144562897[65] = 0.0;
   out_7704822479144562897[66] = 0.0;
   out_7704822479144562897[67] = 0.0;
   out_7704822479144562897[68] = 0.0;
   out_7704822479144562897[69] = 0.0;
   out_7704822479144562897[70] = 1.0;
   out_7704822479144562897[71] = 0.0;
   out_7704822479144562897[72] = 0.0;
   out_7704822479144562897[73] = 0.0;
   out_7704822479144562897[74] = 0.0;
   out_7704822479144562897[75] = 0.0;
   out_7704822479144562897[76] = 0.0;
   out_7704822479144562897[77] = 0.0;
   out_7704822479144562897[78] = 0.0;
   out_7704822479144562897[79] = 0.0;
   out_7704822479144562897[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_2423168834336223124) {
   out_2423168834336223124[0] = state[0];
   out_2423168834336223124[1] = state[1];
   out_2423168834336223124[2] = state[2];
   out_2423168834336223124[3] = state[3];
   out_2423168834336223124[4] = state[4];
   out_2423168834336223124[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_2423168834336223124[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_2423168834336223124[7] = state[7];
   out_2423168834336223124[8] = state[8];
}
void F_fun(double *state, double dt, double *out_7639588574330807467) {
   out_7639588574330807467[0] = 1;
   out_7639588574330807467[1] = 0;
   out_7639588574330807467[2] = 0;
   out_7639588574330807467[3] = 0;
   out_7639588574330807467[4] = 0;
   out_7639588574330807467[5] = 0;
   out_7639588574330807467[6] = 0;
   out_7639588574330807467[7] = 0;
   out_7639588574330807467[8] = 0;
   out_7639588574330807467[9] = 0;
   out_7639588574330807467[10] = 1;
   out_7639588574330807467[11] = 0;
   out_7639588574330807467[12] = 0;
   out_7639588574330807467[13] = 0;
   out_7639588574330807467[14] = 0;
   out_7639588574330807467[15] = 0;
   out_7639588574330807467[16] = 0;
   out_7639588574330807467[17] = 0;
   out_7639588574330807467[18] = 0;
   out_7639588574330807467[19] = 0;
   out_7639588574330807467[20] = 1;
   out_7639588574330807467[21] = 0;
   out_7639588574330807467[22] = 0;
   out_7639588574330807467[23] = 0;
   out_7639588574330807467[24] = 0;
   out_7639588574330807467[25] = 0;
   out_7639588574330807467[26] = 0;
   out_7639588574330807467[27] = 0;
   out_7639588574330807467[28] = 0;
   out_7639588574330807467[29] = 0;
   out_7639588574330807467[30] = 1;
   out_7639588574330807467[31] = 0;
   out_7639588574330807467[32] = 0;
   out_7639588574330807467[33] = 0;
   out_7639588574330807467[34] = 0;
   out_7639588574330807467[35] = 0;
   out_7639588574330807467[36] = 0;
   out_7639588574330807467[37] = 0;
   out_7639588574330807467[38] = 0;
   out_7639588574330807467[39] = 0;
   out_7639588574330807467[40] = 1;
   out_7639588574330807467[41] = 0;
   out_7639588574330807467[42] = 0;
   out_7639588574330807467[43] = 0;
   out_7639588574330807467[44] = 0;
   out_7639588574330807467[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_7639588574330807467[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_7639588574330807467[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_7639588574330807467[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_7639588574330807467[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_7639588574330807467[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_7639588574330807467[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_7639588574330807467[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_7639588574330807467[53] = -9.8100000000000005*dt;
   out_7639588574330807467[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_7639588574330807467[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_7639588574330807467[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_7639588574330807467[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_7639588574330807467[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_7639588574330807467[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_7639588574330807467[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_7639588574330807467[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_7639588574330807467[62] = 0;
   out_7639588574330807467[63] = 0;
   out_7639588574330807467[64] = 0;
   out_7639588574330807467[65] = 0;
   out_7639588574330807467[66] = 0;
   out_7639588574330807467[67] = 0;
   out_7639588574330807467[68] = 0;
   out_7639588574330807467[69] = 0;
   out_7639588574330807467[70] = 1;
   out_7639588574330807467[71] = 0;
   out_7639588574330807467[72] = 0;
   out_7639588574330807467[73] = 0;
   out_7639588574330807467[74] = 0;
   out_7639588574330807467[75] = 0;
   out_7639588574330807467[76] = 0;
   out_7639588574330807467[77] = 0;
   out_7639588574330807467[78] = 0;
   out_7639588574330807467[79] = 0;
   out_7639588574330807467[80] = 1;
}
void h_25(double *state, double *unused, double *out_4973933158632202337) {
   out_4973933158632202337[0] = state[6];
}
void H_25(double *state, double *unused, double *out_1488365746767674340) {
   out_1488365746767674340[0] = 0;
   out_1488365746767674340[1] = 0;
   out_1488365746767674340[2] = 0;
   out_1488365746767674340[3] = 0;
   out_1488365746767674340[4] = 0;
   out_1488365746767674340[5] = 0;
   out_1488365746767674340[6] = 1;
   out_1488365746767674340[7] = 0;
   out_1488365746767674340[8] = 0;
}
void h_24(double *state, double *unused, double *out_8075656837058392290) {
   out_8075656837058392290[0] = state[4];
   out_8075656837058392290[1] = state[5];
}
void H_24(double *state, double *unused, double *out_688848676839475633) {
   out_688848676839475633[0] = 0;
   out_688848676839475633[1] = 0;
   out_688848676839475633[2] = 0;
   out_688848676839475633[3] = 0;
   out_688848676839475633[4] = 1;
   out_688848676839475633[5] = 0;
   out_688848676839475633[6] = 0;
   out_688848676839475633[7] = 0;
   out_688848676839475633[8] = 0;
   out_688848676839475633[9] = 0;
   out_688848676839475633[10] = 0;
   out_688848676839475633[11] = 0;
   out_688848676839475633[12] = 0;
   out_688848676839475633[13] = 0;
   out_688848676839475633[14] = 1;
   out_688848676839475633[15] = 0;
   out_688848676839475633[16] = 0;
   out_688848676839475633[17] = 0;
}
void h_30(double *state, double *unused, double *out_4816746490281073192) {
   out_4816746490281073192[0] = state[4];
}
void H_30(double *state, double *unused, double *out_1029967211739574287) {
   out_1029967211739574287[0] = 0;
   out_1029967211739574287[1] = 0;
   out_1029967211739574287[2] = 0;
   out_1029967211739574287[3] = 0;
   out_1029967211739574287[4] = 1;
   out_1029967211739574287[5] = 0;
   out_1029967211739574287[6] = 0;
   out_1029967211739574287[7] = 0;
   out_1029967211739574287[8] = 0;
}
void h_26(double *state, double *unused, double *out_2119428105077637665) {
   out_2119428105077637665[0] = state[7];
}
void H_26(double *state, double *unused, double *out_5229869065641730564) {
   out_5229869065641730564[0] = 0;
   out_5229869065641730564[1] = 0;
   out_5229869065641730564[2] = 0;
   out_5229869065641730564[3] = 0;
   out_5229869065641730564[4] = 0;
   out_5229869065641730564[5] = 0;
   out_5229869065641730564[6] = 0;
   out_5229869065641730564[7] = 1;
   out_5229869065641730564[8] = 0;
}
void h_27(double *state, double *unused, double *out_2161381055362348954) {
   out_2161381055362348954[0] = state[3];
}
void H_27(double *state, double *unused, double *out_3253561282923517504) {
   out_3253561282923517504[0] = 0;
   out_3253561282923517504[1] = 0;
   out_3253561282923517504[2] = 0;
   out_3253561282923517504[3] = 1;
   out_3253561282923517504[4] = 0;
   out_3253561282923517504[5] = 0;
   out_3253561282923517504[6] = 0;
   out_3253561282923517504[7] = 0;
   out_3253561282923517504[8] = 0;
}
void h_29(double *state, double *unused, double *out_2436575117646854843) {
   out_2436575117646854843[0] = state[1];
}
void H_29(double *state, double *unused, double *out_1540198556053966471) {
   out_1540198556053966471[0] = 0;
   out_1540198556053966471[1] = 1;
   out_1540198556053966471[2] = 0;
   out_1540198556053966471[3] = 0;
   out_1540198556053966471[4] = 0;
   out_1540198556053966471[5] = 0;
   out_1540198556053966471[6] = 0;
   out_1540198556053966471[7] = 0;
   out_1540198556053966471[8] = 0;
}
void h_28(double *state, double *unused, double *out_7163054323023194599) {
   out_7163054323023194599[0] = state[0];
}
void H_28(double *state, double *unused, double *out_3542200461015564103) {
   out_3542200461015564103[0] = 1;
   out_3542200461015564103[1] = 0;
   out_3542200461015564103[2] = 0;
   out_3542200461015564103[3] = 0;
   out_3542200461015564103[4] = 0;
   out_3542200461015564103[5] = 0;
   out_3542200461015564103[6] = 0;
   out_3542200461015564103[7] = 0;
   out_3542200461015564103[8] = 0;
}
void h_31(double *state, double *unused, double *out_1389660819669613524) {
   out_1389660819669613524[0] = state[8];
}
void H_31(double *state, double *unused, double *out_1457719784890713912) {
   out_1457719784890713912[0] = 0;
   out_1457719784890713912[1] = 0;
   out_1457719784890713912[2] = 0;
   out_1457719784890713912[3] = 0;
   out_1457719784890713912[4] = 0;
   out_1457719784890713912[5] = 0;
   out_1457719784890713912[6] = 0;
   out_1457719784890713912[7] = 0;
   out_1457719784890713912[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_4191231468621882354) {
  err_fun(nom_x, delta_x, out_4191231468621882354);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_4409511713992133464) {
  inv_err_fun(nom_x, true_x, out_4409511713992133464);
}
void car_H_mod_fun(double *state, double *out_7704822479144562897) {
  H_mod_fun(state, out_7704822479144562897);
}
void car_f_fun(double *state, double dt, double *out_2423168834336223124) {
  f_fun(state,  dt, out_2423168834336223124);
}
void car_F_fun(double *state, double dt, double *out_7639588574330807467) {
  F_fun(state,  dt, out_7639588574330807467);
}
void car_h_25(double *state, double *unused, double *out_4973933158632202337) {
  h_25(state, unused, out_4973933158632202337);
}
void car_H_25(double *state, double *unused, double *out_1488365746767674340) {
  H_25(state, unused, out_1488365746767674340);
}
void car_h_24(double *state, double *unused, double *out_8075656837058392290) {
  h_24(state, unused, out_8075656837058392290);
}
void car_H_24(double *state, double *unused, double *out_688848676839475633) {
  H_24(state, unused, out_688848676839475633);
}
void car_h_30(double *state, double *unused, double *out_4816746490281073192) {
  h_30(state, unused, out_4816746490281073192);
}
void car_H_30(double *state, double *unused, double *out_1029967211739574287) {
  H_30(state, unused, out_1029967211739574287);
}
void car_h_26(double *state, double *unused, double *out_2119428105077637665) {
  h_26(state, unused, out_2119428105077637665);
}
void car_H_26(double *state, double *unused, double *out_5229869065641730564) {
  H_26(state, unused, out_5229869065641730564);
}
void car_h_27(double *state, double *unused, double *out_2161381055362348954) {
  h_27(state, unused, out_2161381055362348954);
}
void car_H_27(double *state, double *unused, double *out_3253561282923517504) {
  H_27(state, unused, out_3253561282923517504);
}
void car_h_29(double *state, double *unused, double *out_2436575117646854843) {
  h_29(state, unused, out_2436575117646854843);
}
void car_H_29(double *state, double *unused, double *out_1540198556053966471) {
  H_29(state, unused, out_1540198556053966471);
}
void car_h_28(double *state, double *unused, double *out_7163054323023194599) {
  h_28(state, unused, out_7163054323023194599);
}
void car_H_28(double *state, double *unused, double *out_3542200461015564103) {
  H_28(state, unused, out_3542200461015564103);
}
void car_h_31(double *state, double *unused, double *out_1389660819669613524) {
  h_31(state, unused, out_1389660819669613524);
}
void car_H_31(double *state, double *unused, double *out_1457719784890713912) {
  H_31(state, unused, out_1457719784890713912);
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
