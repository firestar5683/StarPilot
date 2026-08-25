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
void err_fun(double *nom_x, double *delta_x, double *out_6066785079692700737) {
   out_6066785079692700737[0] = delta_x[0] + nom_x[0];
   out_6066785079692700737[1] = delta_x[1] + nom_x[1];
   out_6066785079692700737[2] = delta_x[2] + nom_x[2];
   out_6066785079692700737[3] = delta_x[3] + nom_x[3];
   out_6066785079692700737[4] = delta_x[4] + nom_x[4];
   out_6066785079692700737[5] = delta_x[5] + nom_x[5];
   out_6066785079692700737[6] = delta_x[6] + nom_x[6];
   out_6066785079692700737[7] = delta_x[7] + nom_x[7];
   out_6066785079692700737[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_386653618683565600) {
   out_386653618683565600[0] = -nom_x[0] + true_x[0];
   out_386653618683565600[1] = -nom_x[1] + true_x[1];
   out_386653618683565600[2] = -nom_x[2] + true_x[2];
   out_386653618683565600[3] = -nom_x[3] + true_x[3];
   out_386653618683565600[4] = -nom_x[4] + true_x[4];
   out_386653618683565600[5] = -nom_x[5] + true_x[5];
   out_386653618683565600[6] = -nom_x[6] + true_x[6];
   out_386653618683565600[7] = -nom_x[7] + true_x[7];
   out_386653618683565600[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_2911819638975789429) {
   out_2911819638975789429[0] = 1.0;
   out_2911819638975789429[1] = 0.0;
   out_2911819638975789429[2] = 0.0;
   out_2911819638975789429[3] = 0.0;
   out_2911819638975789429[4] = 0.0;
   out_2911819638975789429[5] = 0.0;
   out_2911819638975789429[6] = 0.0;
   out_2911819638975789429[7] = 0.0;
   out_2911819638975789429[8] = 0.0;
   out_2911819638975789429[9] = 0.0;
   out_2911819638975789429[10] = 1.0;
   out_2911819638975789429[11] = 0.0;
   out_2911819638975789429[12] = 0.0;
   out_2911819638975789429[13] = 0.0;
   out_2911819638975789429[14] = 0.0;
   out_2911819638975789429[15] = 0.0;
   out_2911819638975789429[16] = 0.0;
   out_2911819638975789429[17] = 0.0;
   out_2911819638975789429[18] = 0.0;
   out_2911819638975789429[19] = 0.0;
   out_2911819638975789429[20] = 1.0;
   out_2911819638975789429[21] = 0.0;
   out_2911819638975789429[22] = 0.0;
   out_2911819638975789429[23] = 0.0;
   out_2911819638975789429[24] = 0.0;
   out_2911819638975789429[25] = 0.0;
   out_2911819638975789429[26] = 0.0;
   out_2911819638975789429[27] = 0.0;
   out_2911819638975789429[28] = 0.0;
   out_2911819638975789429[29] = 0.0;
   out_2911819638975789429[30] = 1.0;
   out_2911819638975789429[31] = 0.0;
   out_2911819638975789429[32] = 0.0;
   out_2911819638975789429[33] = 0.0;
   out_2911819638975789429[34] = 0.0;
   out_2911819638975789429[35] = 0.0;
   out_2911819638975789429[36] = 0.0;
   out_2911819638975789429[37] = 0.0;
   out_2911819638975789429[38] = 0.0;
   out_2911819638975789429[39] = 0.0;
   out_2911819638975789429[40] = 1.0;
   out_2911819638975789429[41] = 0.0;
   out_2911819638975789429[42] = 0.0;
   out_2911819638975789429[43] = 0.0;
   out_2911819638975789429[44] = 0.0;
   out_2911819638975789429[45] = 0.0;
   out_2911819638975789429[46] = 0.0;
   out_2911819638975789429[47] = 0.0;
   out_2911819638975789429[48] = 0.0;
   out_2911819638975789429[49] = 0.0;
   out_2911819638975789429[50] = 1.0;
   out_2911819638975789429[51] = 0.0;
   out_2911819638975789429[52] = 0.0;
   out_2911819638975789429[53] = 0.0;
   out_2911819638975789429[54] = 0.0;
   out_2911819638975789429[55] = 0.0;
   out_2911819638975789429[56] = 0.0;
   out_2911819638975789429[57] = 0.0;
   out_2911819638975789429[58] = 0.0;
   out_2911819638975789429[59] = 0.0;
   out_2911819638975789429[60] = 1.0;
   out_2911819638975789429[61] = 0.0;
   out_2911819638975789429[62] = 0.0;
   out_2911819638975789429[63] = 0.0;
   out_2911819638975789429[64] = 0.0;
   out_2911819638975789429[65] = 0.0;
   out_2911819638975789429[66] = 0.0;
   out_2911819638975789429[67] = 0.0;
   out_2911819638975789429[68] = 0.0;
   out_2911819638975789429[69] = 0.0;
   out_2911819638975789429[70] = 1.0;
   out_2911819638975789429[71] = 0.0;
   out_2911819638975789429[72] = 0.0;
   out_2911819638975789429[73] = 0.0;
   out_2911819638975789429[74] = 0.0;
   out_2911819638975789429[75] = 0.0;
   out_2911819638975789429[76] = 0.0;
   out_2911819638975789429[77] = 0.0;
   out_2911819638975789429[78] = 0.0;
   out_2911819638975789429[79] = 0.0;
   out_2911819638975789429[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_7908585330617552733) {
   out_7908585330617552733[0] = state[0];
   out_7908585330617552733[1] = state[1];
   out_7908585330617552733[2] = state[2];
   out_7908585330617552733[3] = state[3];
   out_7908585330617552733[4] = state[4];
   out_7908585330617552733[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_7908585330617552733[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_7908585330617552733[7] = state[7];
   out_7908585330617552733[8] = state[8];
}
void F_fun(double *state, double dt, double *out_3633424257345620011) {
   out_3633424257345620011[0] = 1;
   out_3633424257345620011[1] = 0;
   out_3633424257345620011[2] = 0;
   out_3633424257345620011[3] = 0;
   out_3633424257345620011[4] = 0;
   out_3633424257345620011[5] = 0;
   out_3633424257345620011[6] = 0;
   out_3633424257345620011[7] = 0;
   out_3633424257345620011[8] = 0;
   out_3633424257345620011[9] = 0;
   out_3633424257345620011[10] = 1;
   out_3633424257345620011[11] = 0;
   out_3633424257345620011[12] = 0;
   out_3633424257345620011[13] = 0;
   out_3633424257345620011[14] = 0;
   out_3633424257345620011[15] = 0;
   out_3633424257345620011[16] = 0;
   out_3633424257345620011[17] = 0;
   out_3633424257345620011[18] = 0;
   out_3633424257345620011[19] = 0;
   out_3633424257345620011[20] = 1;
   out_3633424257345620011[21] = 0;
   out_3633424257345620011[22] = 0;
   out_3633424257345620011[23] = 0;
   out_3633424257345620011[24] = 0;
   out_3633424257345620011[25] = 0;
   out_3633424257345620011[26] = 0;
   out_3633424257345620011[27] = 0;
   out_3633424257345620011[28] = 0;
   out_3633424257345620011[29] = 0;
   out_3633424257345620011[30] = 1;
   out_3633424257345620011[31] = 0;
   out_3633424257345620011[32] = 0;
   out_3633424257345620011[33] = 0;
   out_3633424257345620011[34] = 0;
   out_3633424257345620011[35] = 0;
   out_3633424257345620011[36] = 0;
   out_3633424257345620011[37] = 0;
   out_3633424257345620011[38] = 0;
   out_3633424257345620011[39] = 0;
   out_3633424257345620011[40] = 1;
   out_3633424257345620011[41] = 0;
   out_3633424257345620011[42] = 0;
   out_3633424257345620011[43] = 0;
   out_3633424257345620011[44] = 0;
   out_3633424257345620011[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_3633424257345620011[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_3633424257345620011[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_3633424257345620011[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_3633424257345620011[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_3633424257345620011[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_3633424257345620011[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_3633424257345620011[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_3633424257345620011[53] = -9.8100000000000005*dt;
   out_3633424257345620011[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_3633424257345620011[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_3633424257345620011[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_3633424257345620011[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_3633424257345620011[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_3633424257345620011[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_3633424257345620011[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_3633424257345620011[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_3633424257345620011[62] = 0;
   out_3633424257345620011[63] = 0;
   out_3633424257345620011[64] = 0;
   out_3633424257345620011[65] = 0;
   out_3633424257345620011[66] = 0;
   out_3633424257345620011[67] = 0;
   out_3633424257345620011[68] = 0;
   out_3633424257345620011[69] = 0;
   out_3633424257345620011[70] = 1;
   out_3633424257345620011[71] = 0;
   out_3633424257345620011[72] = 0;
   out_3633424257345620011[73] = 0;
   out_3633424257345620011[74] = 0;
   out_3633424257345620011[75] = 0;
   out_3633424257345620011[76] = 0;
   out_3633424257345620011[77] = 0;
   out_3633424257345620011[78] = 0;
   out_3633424257345620011[79] = 0;
   out_3633424257345620011[80] = 1;
}
void h_25(double *state, double *unused, double *out_8566594812092318047) {
   out_8566594812092318047[0] = state[6];
}
void H_25(double *state, double *unused, double *out_3585203320914240522) {
   out_3585203320914240522[0] = 0;
   out_3585203320914240522[1] = 0;
   out_3585203320914240522[2] = 0;
   out_3585203320914240522[3] = 0;
   out_3585203320914240522[4] = 0;
   out_3585203320914240522[5] = 0;
   out_3585203320914240522[6] = 1;
   out_3585203320914240522[7] = 0;
   out_3585203320914240522[8] = 0;
}
void h_24(double *state, double *unused, double *out_7709351917136459488) {
   out_7709351917136459488[0] = state[4];
   out_7709351917136459488[1] = state[5];
}
void H_24(double *state, double *unused, double *out_4055660802957579246) {
   out_4055660802957579246[0] = 0;
   out_4055660802957579246[1] = 0;
   out_4055660802957579246[2] = 0;
   out_4055660802957579246[3] = 0;
   out_4055660802957579246[4] = 1;
   out_4055660802957579246[5] = 0;
   out_4055660802957579246[6] = 0;
   out_4055660802957579246[7] = 0;
   out_4055660802957579246[8] = 0;
   out_4055660802957579246[9] = 0;
   out_4055660802957579246[10] = 0;
   out_4055660802957579246[11] = 0;
   out_4055660802957579246[12] = 0;
   out_4055660802957579246[13] = 0;
   out_4055660802957579246[14] = 1;
   out_4055660802957579246[15] = 0;
   out_4055660802957579246[16] = 0;
   out_4055660802957579246[17] = 0;
}
void h_30(double *state, double *unused, double *out_3060647100788456434) {
   out_3060647100788456434[0] = state[4];
}
void H_30(double *state, double *unused, double *out_3714542268057480592) {
   out_3714542268057480592[0] = 0;
   out_3714542268057480592[1] = 0;
   out_3714542268057480592[2] = 0;
   out_3714542268057480592[3] = 0;
   out_3714542268057480592[4] = 1;
   out_3714542268057480592[5] = 0;
   out_3714542268057480592[6] = 0;
   out_3714542268057480592[7] = 0;
   out_3714542268057480592[8] = 0;
}
void h_26(double *state, double *unused, double *out_2806316718466979703) {
   out_2806316718466979703[0] = state[7];
}
void H_26(double *state, double *unused, double *out_7326706639788296746) {
   out_7326706639788296746[0] = 0;
   out_7326706639788296746[1] = 0;
   out_7326706639788296746[2] = 0;
   out_7326706639788296746[3] = 0;
   out_7326706639788296746[4] = 0;
   out_7326706639788296746[5] = 0;
   out_7326706639788296746[6] = 0;
   out_7326706639788296746[7] = 1;
   out_7326706639788296746[8] = 0;
}
void h_27(double *state, double *unused, double *out_8520521730607863741) {
   out_8520521730607863741[0] = state[3];
}
void H_27(double *state, double *unused, double *out_5889305579857905503) {
   out_5889305579857905503[0] = 0;
   out_5889305579857905503[1] = 0;
   out_5889305579857905503[2] = 0;
   out_5889305579857905503[3] = 1;
   out_5889305579857905503[4] = 0;
   out_5889305579857905503[5] = 0;
   out_5889305579857905503[6] = 0;
   out_5889305579857905503[7] = 0;
   out_5889305579857905503[8] = 0;
}
void h_29(double *state, double *unused, double *out_617195554075987441) {
   out_617195554075987441[0] = state[1];
}
void H_29(double *state, double *unused, double *out_7602668306727456536) {
   out_7602668306727456536[0] = 0;
   out_7602668306727456536[1] = 1;
   out_7602668306727456536[2] = 0;
   out_7602668306727456536[3] = 0;
   out_7602668306727456536[4] = 0;
   out_7602668306727456536[5] = 0;
   out_7602668306727456536[6] = 0;
   out_7602668306727456536[7] = 0;
   out_7602668306727456536[8] = 0;
}
void h_28(double *state, double *unused, double *out_8625997807319031960) {
   out_8625997807319031960[0] = state[0];
}
void H_28(double *state, double *unused, double *out_5761676749912564506) {
   out_5761676749912564506[0] = 1;
   out_5761676749912564506[1] = 0;
   out_5761676749912564506[2] = 0;
   out_5761676749912564506[3] = 0;
   out_5761676749912564506[4] = 0;
   out_5761676749912564506[5] = 0;
   out_5761676749912564506[6] = 0;
   out_5761676749912564506[7] = 0;
   out_5761676749912564506[8] = 0;
}
void h_31(double *state, double *unused, double *out_7164630353941861079) {
   out_7164630353941861079[0] = state[8];
}
void H_31(double *state, double *unused, double *out_3554557359037280094) {
   out_3554557359037280094[0] = 0;
   out_3554557359037280094[1] = 0;
   out_3554557359037280094[2] = 0;
   out_3554557359037280094[3] = 0;
   out_3554557359037280094[4] = 0;
   out_3554557359037280094[5] = 0;
   out_3554557359037280094[6] = 0;
   out_3554557359037280094[7] = 0;
   out_3554557359037280094[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_6066785079692700737) {
  err_fun(nom_x, delta_x, out_6066785079692700737);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_386653618683565600) {
  inv_err_fun(nom_x, true_x, out_386653618683565600);
}
void car_H_mod_fun(double *state, double *out_2911819638975789429) {
  H_mod_fun(state, out_2911819638975789429);
}
void car_f_fun(double *state, double dt, double *out_7908585330617552733) {
  f_fun(state,  dt, out_7908585330617552733);
}
void car_F_fun(double *state, double dt, double *out_3633424257345620011) {
  F_fun(state,  dt, out_3633424257345620011);
}
void car_h_25(double *state, double *unused, double *out_8566594812092318047) {
  h_25(state, unused, out_8566594812092318047);
}
void car_H_25(double *state, double *unused, double *out_3585203320914240522) {
  H_25(state, unused, out_3585203320914240522);
}
void car_h_24(double *state, double *unused, double *out_7709351917136459488) {
  h_24(state, unused, out_7709351917136459488);
}
void car_H_24(double *state, double *unused, double *out_4055660802957579246) {
  H_24(state, unused, out_4055660802957579246);
}
void car_h_30(double *state, double *unused, double *out_3060647100788456434) {
  h_30(state, unused, out_3060647100788456434);
}
void car_H_30(double *state, double *unused, double *out_3714542268057480592) {
  H_30(state, unused, out_3714542268057480592);
}
void car_h_26(double *state, double *unused, double *out_2806316718466979703) {
  h_26(state, unused, out_2806316718466979703);
}
void car_H_26(double *state, double *unused, double *out_7326706639788296746) {
  H_26(state, unused, out_7326706639788296746);
}
void car_h_27(double *state, double *unused, double *out_8520521730607863741) {
  h_27(state, unused, out_8520521730607863741);
}
void car_H_27(double *state, double *unused, double *out_5889305579857905503) {
  H_27(state, unused, out_5889305579857905503);
}
void car_h_29(double *state, double *unused, double *out_617195554075987441) {
  h_29(state, unused, out_617195554075987441);
}
void car_H_29(double *state, double *unused, double *out_7602668306727456536) {
  H_29(state, unused, out_7602668306727456536);
}
void car_h_28(double *state, double *unused, double *out_8625997807319031960) {
  h_28(state, unused, out_8625997807319031960);
}
void car_H_28(double *state, double *unused, double *out_5761676749912564506) {
  H_28(state, unused, out_5761676749912564506);
}
void car_h_31(double *state, double *unused, double *out_7164630353941861079) {
  h_31(state, unused, out_7164630353941861079);
}
void car_H_31(double *state, double *unused, double *out_3554557359037280094) {
  H_31(state, unused, out_3554557359037280094);
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
