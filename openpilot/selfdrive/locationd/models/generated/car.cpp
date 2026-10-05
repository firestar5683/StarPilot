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
void err_fun(double *nom_x, double *delta_x, double *out_6746218398639626110) {
   out_6746218398639626110[0] = delta_x[0] + nom_x[0];
   out_6746218398639626110[1] = delta_x[1] + nom_x[1];
   out_6746218398639626110[2] = delta_x[2] + nom_x[2];
   out_6746218398639626110[3] = delta_x[3] + nom_x[3];
   out_6746218398639626110[4] = delta_x[4] + nom_x[4];
   out_6746218398639626110[5] = delta_x[5] + nom_x[5];
   out_6746218398639626110[6] = delta_x[6] + nom_x[6];
   out_6746218398639626110[7] = delta_x[7] + nom_x[7];
   out_6746218398639626110[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_8789333614403809544) {
   out_8789333614403809544[0] = -nom_x[0] + true_x[0];
   out_8789333614403809544[1] = -nom_x[1] + true_x[1];
   out_8789333614403809544[2] = -nom_x[2] + true_x[2];
   out_8789333614403809544[3] = -nom_x[3] + true_x[3];
   out_8789333614403809544[4] = -nom_x[4] + true_x[4];
   out_8789333614403809544[5] = -nom_x[5] + true_x[5];
   out_8789333614403809544[6] = -nom_x[6] + true_x[6];
   out_8789333614403809544[7] = -nom_x[7] + true_x[7];
   out_8789333614403809544[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_5287356164479477201) {
   out_5287356164479477201[0] = 1.0;
   out_5287356164479477201[1] = 0.0;
   out_5287356164479477201[2] = 0.0;
   out_5287356164479477201[3] = 0.0;
   out_5287356164479477201[4] = 0.0;
   out_5287356164479477201[5] = 0.0;
   out_5287356164479477201[6] = 0.0;
   out_5287356164479477201[7] = 0.0;
   out_5287356164479477201[8] = 0.0;
   out_5287356164479477201[9] = 0.0;
   out_5287356164479477201[10] = 1.0;
   out_5287356164479477201[11] = 0.0;
   out_5287356164479477201[12] = 0.0;
   out_5287356164479477201[13] = 0.0;
   out_5287356164479477201[14] = 0.0;
   out_5287356164479477201[15] = 0.0;
   out_5287356164479477201[16] = 0.0;
   out_5287356164479477201[17] = 0.0;
   out_5287356164479477201[18] = 0.0;
   out_5287356164479477201[19] = 0.0;
   out_5287356164479477201[20] = 1.0;
   out_5287356164479477201[21] = 0.0;
   out_5287356164479477201[22] = 0.0;
   out_5287356164479477201[23] = 0.0;
   out_5287356164479477201[24] = 0.0;
   out_5287356164479477201[25] = 0.0;
   out_5287356164479477201[26] = 0.0;
   out_5287356164479477201[27] = 0.0;
   out_5287356164479477201[28] = 0.0;
   out_5287356164479477201[29] = 0.0;
   out_5287356164479477201[30] = 1.0;
   out_5287356164479477201[31] = 0.0;
   out_5287356164479477201[32] = 0.0;
   out_5287356164479477201[33] = 0.0;
   out_5287356164479477201[34] = 0.0;
   out_5287356164479477201[35] = 0.0;
   out_5287356164479477201[36] = 0.0;
   out_5287356164479477201[37] = 0.0;
   out_5287356164479477201[38] = 0.0;
   out_5287356164479477201[39] = 0.0;
   out_5287356164479477201[40] = 1.0;
   out_5287356164479477201[41] = 0.0;
   out_5287356164479477201[42] = 0.0;
   out_5287356164479477201[43] = 0.0;
   out_5287356164479477201[44] = 0.0;
   out_5287356164479477201[45] = 0.0;
   out_5287356164479477201[46] = 0.0;
   out_5287356164479477201[47] = 0.0;
   out_5287356164479477201[48] = 0.0;
   out_5287356164479477201[49] = 0.0;
   out_5287356164479477201[50] = 1.0;
   out_5287356164479477201[51] = 0.0;
   out_5287356164479477201[52] = 0.0;
   out_5287356164479477201[53] = 0.0;
   out_5287356164479477201[54] = 0.0;
   out_5287356164479477201[55] = 0.0;
   out_5287356164479477201[56] = 0.0;
   out_5287356164479477201[57] = 0.0;
   out_5287356164479477201[58] = 0.0;
   out_5287356164479477201[59] = 0.0;
   out_5287356164479477201[60] = 1.0;
   out_5287356164479477201[61] = 0.0;
   out_5287356164479477201[62] = 0.0;
   out_5287356164479477201[63] = 0.0;
   out_5287356164479477201[64] = 0.0;
   out_5287356164479477201[65] = 0.0;
   out_5287356164479477201[66] = 0.0;
   out_5287356164479477201[67] = 0.0;
   out_5287356164479477201[68] = 0.0;
   out_5287356164479477201[69] = 0.0;
   out_5287356164479477201[70] = 1.0;
   out_5287356164479477201[71] = 0.0;
   out_5287356164479477201[72] = 0.0;
   out_5287356164479477201[73] = 0.0;
   out_5287356164479477201[74] = 0.0;
   out_5287356164479477201[75] = 0.0;
   out_5287356164479477201[76] = 0.0;
   out_5287356164479477201[77] = 0.0;
   out_5287356164479477201[78] = 0.0;
   out_5287356164479477201[79] = 0.0;
   out_5287356164479477201[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_4463126409710139018) {
   out_4463126409710139018[0] = state[0];
   out_4463126409710139018[1] = state[1];
   out_4463126409710139018[2] = state[2];
   out_4463126409710139018[3] = state[3];
   out_4463126409710139018[4] = state[4];
   out_4463126409710139018[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_4463126409710139018[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_4463126409710139018[7] = state[7];
   out_4463126409710139018[8] = state[8];
}
void F_fun(double *state, double dt, double *out_6080121800310696988) {
   out_6080121800310696988[0] = 1;
   out_6080121800310696988[1] = 0;
   out_6080121800310696988[2] = 0;
   out_6080121800310696988[3] = 0;
   out_6080121800310696988[4] = 0;
   out_6080121800310696988[5] = 0;
   out_6080121800310696988[6] = 0;
   out_6080121800310696988[7] = 0;
   out_6080121800310696988[8] = 0;
   out_6080121800310696988[9] = 0;
   out_6080121800310696988[10] = 1;
   out_6080121800310696988[11] = 0;
   out_6080121800310696988[12] = 0;
   out_6080121800310696988[13] = 0;
   out_6080121800310696988[14] = 0;
   out_6080121800310696988[15] = 0;
   out_6080121800310696988[16] = 0;
   out_6080121800310696988[17] = 0;
   out_6080121800310696988[18] = 0;
   out_6080121800310696988[19] = 0;
   out_6080121800310696988[20] = 1;
   out_6080121800310696988[21] = 0;
   out_6080121800310696988[22] = 0;
   out_6080121800310696988[23] = 0;
   out_6080121800310696988[24] = 0;
   out_6080121800310696988[25] = 0;
   out_6080121800310696988[26] = 0;
   out_6080121800310696988[27] = 0;
   out_6080121800310696988[28] = 0;
   out_6080121800310696988[29] = 0;
   out_6080121800310696988[30] = 1;
   out_6080121800310696988[31] = 0;
   out_6080121800310696988[32] = 0;
   out_6080121800310696988[33] = 0;
   out_6080121800310696988[34] = 0;
   out_6080121800310696988[35] = 0;
   out_6080121800310696988[36] = 0;
   out_6080121800310696988[37] = 0;
   out_6080121800310696988[38] = 0;
   out_6080121800310696988[39] = 0;
   out_6080121800310696988[40] = 1;
   out_6080121800310696988[41] = 0;
   out_6080121800310696988[42] = 0;
   out_6080121800310696988[43] = 0;
   out_6080121800310696988[44] = 0;
   out_6080121800310696988[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_6080121800310696988[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_6080121800310696988[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_6080121800310696988[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_6080121800310696988[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_6080121800310696988[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_6080121800310696988[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_6080121800310696988[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_6080121800310696988[53] = -9.8100000000000005*dt;
   out_6080121800310696988[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_6080121800310696988[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_6080121800310696988[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_6080121800310696988[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_6080121800310696988[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_6080121800310696988[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_6080121800310696988[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_6080121800310696988[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_6080121800310696988[62] = 0;
   out_6080121800310696988[63] = 0;
   out_6080121800310696988[64] = 0;
   out_6080121800310696988[65] = 0;
   out_6080121800310696988[66] = 0;
   out_6080121800310696988[67] = 0;
   out_6080121800310696988[68] = 0;
   out_6080121800310696988[69] = 0;
   out_6080121800310696988[70] = 1;
   out_6080121800310696988[71] = 0;
   out_6080121800310696988[72] = 0;
   out_6080121800310696988[73] = 0;
   out_6080121800310696988[74] = 0;
   out_6080121800310696988[75] = 0;
   out_6080121800310696988[76] = 0;
   out_6080121800310696988[77] = 0;
   out_6080121800310696988[78] = 0;
   out_6080121800310696988[79] = 0;
   out_6080121800310696988[80] = 1;
}
void h_25(double *state, double *unused, double *out_6823959720500200939) {
   out_6823959720500200939[0] = state[6];
}
void H_25(double *state, double *unused, double *out_2633981868494382604) {
   out_2633981868494382604[0] = 0;
   out_2633981868494382604[1] = 0;
   out_2633981868494382604[2] = 0;
   out_2633981868494382604[3] = 0;
   out_2633981868494382604[4] = 0;
   out_2633981868494382604[5] = 0;
   out_2633981868494382604[6] = 1;
   out_2633981868494382604[7] = 0;
   out_2633981868494382604[8] = 0;
}
void h_24(double *state, double *unused, double *out_6472024300223995676) {
   out_6472024300223995676[0] = state[4];
   out_6472024300223995676[1] = state[5];
}
void H_24(double *state, double *unused, double *out_1793550084312337612) {
   out_1793550084312337612[0] = 0;
   out_1793550084312337612[1] = 0;
   out_1793550084312337612[2] = 0;
   out_1793550084312337612[3] = 0;
   out_1793550084312337612[4] = 1;
   out_1793550084312337612[5] = 0;
   out_1793550084312337612[6] = 0;
   out_1793550084312337612[7] = 0;
   out_1793550084312337612[8] = 0;
   out_1793550084312337612[9] = 0;
   out_1793550084312337612[10] = 0;
   out_1793550084312337612[11] = 0;
   out_1793550084312337612[12] = 0;
   out_1793550084312337612[13] = 0;
   out_1793550084312337612[14] = 1;
   out_1793550084312337612[15] = 0;
   out_1793550084312337612[16] = 0;
   out_1793550084312337612[17] = 0;
}
void h_30(double *state, double *unused, double *out_5373328327871317772) {
   out_5373328327871317772[0] = state[4];
}
void H_30(double *state, double *unused, double *out_1893714461633225594) {
   out_1893714461633225594[0] = 0;
   out_1893714461633225594[1] = 0;
   out_1893714461633225594[2] = 0;
   out_1893714461633225594[3] = 0;
   out_1893714461633225594[4] = 1;
   out_1893714461633225594[5] = 0;
   out_1893714461633225594[6] = 0;
   out_1893714461633225594[7] = 0;
   out_1893714461633225594[8] = 0;
}
void h_26(double *state, double *unused, double *out_8185880431141171155) {
   out_8185880431141171155[0] = state[7];
}
void H_26(double *state, double *unused, double *out_1107521450379673620) {
   out_1107521450379673620[0] = 0;
   out_1107521450379673620[1] = 0;
   out_1107521450379673620[2] = 0;
   out_1107521450379673620[3] = 0;
   out_1107521450379673620[4] = 0;
   out_1107521450379673620[5] = 0;
   out_1107521450379673620[6] = 0;
   out_1107521450379673620[7] = 1;
   out_1107521450379673620[8] = 0;
}
void h_27(double *state, double *unused, double *out_178802983292864840) {
   out_178802983292864840[0] = state[3];
}
void H_27(double *state, double *unused, double *out_4068477773433650505) {
   out_4068477773433650505[0] = 0;
   out_4068477773433650505[1] = 0;
   out_4068477773433650505[2] = 0;
   out_4068477773433650505[3] = 1;
   out_4068477773433650505[4] = 0;
   out_4068477773433650505[5] = 0;
   out_4068477773433650505[6] = 0;
   out_4068477773433650505[7] = 0;
   out_4068477773433650505[8] = 0;
}
void h_29(double *state, double *unused, double *out_8071742478177388199) {
   out_8071742478177388199[0] = state[1];
}
void H_29(double *state, double *unused, double *out_1383483117318833410) {
   out_1383483117318833410[0] = 0;
   out_1383483117318833410[1] = 1;
   out_1383483117318833410[2] = 0;
   out_1383483117318833410[3] = 0;
   out_1383483117318833410[4] = 0;
   out_1383483117318833410[5] = 0;
   out_1383483117318833410[6] = 0;
   out_1383483117318833410[7] = 0;
   out_1383483117318833410[8] = 0;
}
void h_28(double *state, double *unused, double *out_9160772155299705605) {
   out_9160772155299705605[0] = state[0];
}
void H_28(double *state, double *unused, double *out_6465882134388363984) {
   out_6465882134388363984[0] = 1;
   out_6465882134388363984[1] = 0;
   out_6465882134388363984[2] = 0;
   out_6465882134388363984[3] = 0;
   out_6465882134388363984[4] = 0;
   out_6465882134388363984[5] = 0;
   out_6465882134388363984[6] = 0;
   out_6465882134388363984[7] = 0;
   out_6465882134388363984[8] = 0;
}
void h_31(double *state, double *unused, double *out_4419568396223364707) {
   out_4419568396223364707[0] = state[8];
}
void H_31(double *state, double *unused, double *out_1733729552613025096) {
   out_1733729552613025096[0] = 0;
   out_1733729552613025096[1] = 0;
   out_1733729552613025096[2] = 0;
   out_1733729552613025096[3] = 0;
   out_1733729552613025096[4] = 0;
   out_1733729552613025096[5] = 0;
   out_1733729552613025096[6] = 0;
   out_1733729552613025096[7] = 0;
   out_1733729552613025096[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_6746218398639626110) {
  err_fun(nom_x, delta_x, out_6746218398639626110);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_8789333614403809544) {
  inv_err_fun(nom_x, true_x, out_8789333614403809544);
}
void car_H_mod_fun(double *state, double *out_5287356164479477201) {
  H_mod_fun(state, out_5287356164479477201);
}
void car_f_fun(double *state, double dt, double *out_4463126409710139018) {
  f_fun(state,  dt, out_4463126409710139018);
}
void car_F_fun(double *state, double dt, double *out_6080121800310696988) {
  F_fun(state,  dt, out_6080121800310696988);
}
void car_h_25(double *state, double *unused, double *out_6823959720500200939) {
  h_25(state, unused, out_6823959720500200939);
}
void car_H_25(double *state, double *unused, double *out_2633981868494382604) {
  H_25(state, unused, out_2633981868494382604);
}
void car_h_24(double *state, double *unused, double *out_6472024300223995676) {
  h_24(state, unused, out_6472024300223995676);
}
void car_H_24(double *state, double *unused, double *out_1793550084312337612) {
  H_24(state, unused, out_1793550084312337612);
}
void car_h_30(double *state, double *unused, double *out_5373328327871317772) {
  h_30(state, unused, out_5373328327871317772);
}
void car_H_30(double *state, double *unused, double *out_1893714461633225594) {
  H_30(state, unused, out_1893714461633225594);
}
void car_h_26(double *state, double *unused, double *out_8185880431141171155) {
  h_26(state, unused, out_8185880431141171155);
}
void car_H_26(double *state, double *unused, double *out_1107521450379673620) {
  H_26(state, unused, out_1107521450379673620);
}
void car_h_27(double *state, double *unused, double *out_178802983292864840) {
  h_27(state, unused, out_178802983292864840);
}
void car_H_27(double *state, double *unused, double *out_4068477773433650505) {
  H_27(state, unused, out_4068477773433650505);
}
void car_h_29(double *state, double *unused, double *out_8071742478177388199) {
  h_29(state, unused, out_8071742478177388199);
}
void car_H_29(double *state, double *unused, double *out_1383483117318833410) {
  H_29(state, unused, out_1383483117318833410);
}
void car_h_28(double *state, double *unused, double *out_9160772155299705605) {
  h_28(state, unused, out_9160772155299705605);
}
void car_H_28(double *state, double *unused, double *out_6465882134388363984) {
  H_28(state, unused, out_6465882134388363984);
}
void car_h_31(double *state, double *unused, double *out_4419568396223364707) {
  h_31(state, unused, out_4419568396223364707);
}
void car_H_31(double *state, double *unused, double *out_1733729552613025096) {
  H_31(state, unused, out_1733729552613025096);
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
