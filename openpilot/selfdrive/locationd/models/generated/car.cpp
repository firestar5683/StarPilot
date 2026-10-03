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
void err_fun(double *nom_x, double *delta_x, double *out_2901723881323854107) {
   out_2901723881323854107[0] = delta_x[0] + nom_x[0];
   out_2901723881323854107[1] = delta_x[1] + nom_x[1];
   out_2901723881323854107[2] = delta_x[2] + nom_x[2];
   out_2901723881323854107[3] = delta_x[3] + nom_x[3];
   out_2901723881323854107[4] = delta_x[4] + nom_x[4];
   out_2901723881323854107[5] = delta_x[5] + nom_x[5];
   out_2901723881323854107[6] = delta_x[6] + nom_x[6];
   out_2901723881323854107[7] = delta_x[7] + nom_x[7];
   out_2901723881323854107[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_2131234716339310483) {
   out_2131234716339310483[0] = -nom_x[0] + true_x[0];
   out_2131234716339310483[1] = -nom_x[1] + true_x[1];
   out_2131234716339310483[2] = -nom_x[2] + true_x[2];
   out_2131234716339310483[3] = -nom_x[3] + true_x[3];
   out_2131234716339310483[4] = -nom_x[4] + true_x[4];
   out_2131234716339310483[5] = -nom_x[5] + true_x[5];
   out_2131234716339310483[6] = -nom_x[6] + true_x[6];
   out_2131234716339310483[7] = -nom_x[7] + true_x[7];
   out_2131234716339310483[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_796115697957996727) {
   out_796115697957996727[0] = 1.0;
   out_796115697957996727[1] = 0.0;
   out_796115697957996727[2] = 0.0;
   out_796115697957996727[3] = 0.0;
   out_796115697957996727[4] = 0.0;
   out_796115697957996727[5] = 0.0;
   out_796115697957996727[6] = 0.0;
   out_796115697957996727[7] = 0.0;
   out_796115697957996727[8] = 0.0;
   out_796115697957996727[9] = 0.0;
   out_796115697957996727[10] = 1.0;
   out_796115697957996727[11] = 0.0;
   out_796115697957996727[12] = 0.0;
   out_796115697957996727[13] = 0.0;
   out_796115697957996727[14] = 0.0;
   out_796115697957996727[15] = 0.0;
   out_796115697957996727[16] = 0.0;
   out_796115697957996727[17] = 0.0;
   out_796115697957996727[18] = 0.0;
   out_796115697957996727[19] = 0.0;
   out_796115697957996727[20] = 1.0;
   out_796115697957996727[21] = 0.0;
   out_796115697957996727[22] = 0.0;
   out_796115697957996727[23] = 0.0;
   out_796115697957996727[24] = 0.0;
   out_796115697957996727[25] = 0.0;
   out_796115697957996727[26] = 0.0;
   out_796115697957996727[27] = 0.0;
   out_796115697957996727[28] = 0.0;
   out_796115697957996727[29] = 0.0;
   out_796115697957996727[30] = 1.0;
   out_796115697957996727[31] = 0.0;
   out_796115697957996727[32] = 0.0;
   out_796115697957996727[33] = 0.0;
   out_796115697957996727[34] = 0.0;
   out_796115697957996727[35] = 0.0;
   out_796115697957996727[36] = 0.0;
   out_796115697957996727[37] = 0.0;
   out_796115697957996727[38] = 0.0;
   out_796115697957996727[39] = 0.0;
   out_796115697957996727[40] = 1.0;
   out_796115697957996727[41] = 0.0;
   out_796115697957996727[42] = 0.0;
   out_796115697957996727[43] = 0.0;
   out_796115697957996727[44] = 0.0;
   out_796115697957996727[45] = 0.0;
   out_796115697957996727[46] = 0.0;
   out_796115697957996727[47] = 0.0;
   out_796115697957996727[48] = 0.0;
   out_796115697957996727[49] = 0.0;
   out_796115697957996727[50] = 1.0;
   out_796115697957996727[51] = 0.0;
   out_796115697957996727[52] = 0.0;
   out_796115697957996727[53] = 0.0;
   out_796115697957996727[54] = 0.0;
   out_796115697957996727[55] = 0.0;
   out_796115697957996727[56] = 0.0;
   out_796115697957996727[57] = 0.0;
   out_796115697957996727[58] = 0.0;
   out_796115697957996727[59] = 0.0;
   out_796115697957996727[60] = 1.0;
   out_796115697957996727[61] = 0.0;
   out_796115697957996727[62] = 0.0;
   out_796115697957996727[63] = 0.0;
   out_796115697957996727[64] = 0.0;
   out_796115697957996727[65] = 0.0;
   out_796115697957996727[66] = 0.0;
   out_796115697957996727[67] = 0.0;
   out_796115697957996727[68] = 0.0;
   out_796115697957996727[69] = 0.0;
   out_796115697957996727[70] = 1.0;
   out_796115697957996727[71] = 0.0;
   out_796115697957996727[72] = 0.0;
   out_796115697957996727[73] = 0.0;
   out_796115697957996727[74] = 0.0;
   out_796115697957996727[75] = 0.0;
   out_796115697957996727[76] = 0.0;
   out_796115697957996727[77] = 0.0;
   out_796115697957996727[78] = 0.0;
   out_796115697957996727[79] = 0.0;
   out_796115697957996727[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_1948741695251664277) {
   out_1948741695251664277[0] = state[0];
   out_1948741695251664277[1] = state[1];
   out_1948741695251664277[2] = state[2];
   out_1948741695251664277[3] = state[3];
   out_1948741695251664277[4] = state[4];
   out_1948741695251664277[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_1948741695251664277[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_1948741695251664277[7] = state[7];
   out_1948741695251664277[8] = state[8];
}
void F_fun(double *state, double dt, double *out_8655261788612512074) {
   out_8655261788612512074[0] = 1;
   out_8655261788612512074[1] = 0;
   out_8655261788612512074[2] = 0;
   out_8655261788612512074[3] = 0;
   out_8655261788612512074[4] = 0;
   out_8655261788612512074[5] = 0;
   out_8655261788612512074[6] = 0;
   out_8655261788612512074[7] = 0;
   out_8655261788612512074[8] = 0;
   out_8655261788612512074[9] = 0;
   out_8655261788612512074[10] = 1;
   out_8655261788612512074[11] = 0;
   out_8655261788612512074[12] = 0;
   out_8655261788612512074[13] = 0;
   out_8655261788612512074[14] = 0;
   out_8655261788612512074[15] = 0;
   out_8655261788612512074[16] = 0;
   out_8655261788612512074[17] = 0;
   out_8655261788612512074[18] = 0;
   out_8655261788612512074[19] = 0;
   out_8655261788612512074[20] = 1;
   out_8655261788612512074[21] = 0;
   out_8655261788612512074[22] = 0;
   out_8655261788612512074[23] = 0;
   out_8655261788612512074[24] = 0;
   out_8655261788612512074[25] = 0;
   out_8655261788612512074[26] = 0;
   out_8655261788612512074[27] = 0;
   out_8655261788612512074[28] = 0;
   out_8655261788612512074[29] = 0;
   out_8655261788612512074[30] = 1;
   out_8655261788612512074[31] = 0;
   out_8655261788612512074[32] = 0;
   out_8655261788612512074[33] = 0;
   out_8655261788612512074[34] = 0;
   out_8655261788612512074[35] = 0;
   out_8655261788612512074[36] = 0;
   out_8655261788612512074[37] = 0;
   out_8655261788612512074[38] = 0;
   out_8655261788612512074[39] = 0;
   out_8655261788612512074[40] = 1;
   out_8655261788612512074[41] = 0;
   out_8655261788612512074[42] = 0;
   out_8655261788612512074[43] = 0;
   out_8655261788612512074[44] = 0;
   out_8655261788612512074[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_8655261788612512074[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_8655261788612512074[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_8655261788612512074[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_8655261788612512074[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_8655261788612512074[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_8655261788612512074[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_8655261788612512074[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_8655261788612512074[53] = -9.8100000000000005*dt;
   out_8655261788612512074[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_8655261788612512074[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_8655261788612512074[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_8655261788612512074[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_8655261788612512074[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_8655261788612512074[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_8655261788612512074[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_8655261788612512074[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_8655261788612512074[62] = 0;
   out_8655261788612512074[63] = 0;
   out_8655261788612512074[64] = 0;
   out_8655261788612512074[65] = 0;
   out_8655261788612512074[66] = 0;
   out_8655261788612512074[67] = 0;
   out_8655261788612512074[68] = 0;
   out_8655261788612512074[69] = 0;
   out_8655261788612512074[70] = 1;
   out_8655261788612512074[71] = 0;
   out_8655261788612512074[72] = 0;
   out_8655261788612512074[73] = 0;
   out_8655261788612512074[74] = 0;
   out_8655261788612512074[75] = 0;
   out_8655261788612512074[76] = 0;
   out_8655261788612512074[77] = 0;
   out_8655261788612512074[78] = 0;
   out_8655261788612512074[79] = 0;
   out_8655261788612512074[80] = 1;
}
void h_25(double *state, double *unused, double *out_3359435300487572769) {
   out_3359435300487572769[0] = state[6];
}
void H_25(double *state, double *unused, double *out_9161258703522981646) {
   out_9161258703522981646[0] = 0;
   out_9161258703522981646[1] = 0;
   out_9161258703522981646[2] = 0;
   out_9161258703522981646[3] = 0;
   out_9161258703522981646[4] = 0;
   out_9161258703522981646[5] = 0;
   out_9161258703522981646[6] = 1;
   out_9161258703522981646[7] = 0;
   out_9161258703522981646[8] = 0;
}
void h_24(double *state, double *unused, double *out_6622515166733284665) {
   out_6622515166733284665[0] = state[4];
   out_6622515166733284665[1] = state[5];
}
void H_24(double *state, double *unused, double *out_8316262094739286247) {
   out_8316262094739286247[0] = 0;
   out_8316262094739286247[1] = 0;
   out_8316262094739286247[2] = 0;
   out_8316262094739286247[3] = 0;
   out_8316262094739286247[4] = 1;
   out_8316262094739286247[5] = 0;
   out_8316262094739286247[6] = 0;
   out_8316262094739286247[7] = 0;
   out_8316262094739286247[8] = 0;
   out_8316262094739286247[9] = 0;
   out_8316262094739286247[10] = 0;
   out_8316262094739286247[11] = 0;
   out_8316262094739286247[12] = 0;
   out_8316262094739286247[13] = 0;
   out_8316262094739286247[14] = 1;
   out_8316262094739286247[15] = 0;
   out_8316262094739286247[16] = 0;
   out_8316262094739286247[17] = 0;
}
void h_30(double *state, double *unused, double *out_411709310132087808) {
   out_411709310132087808[0] = state[4];
}
void H_30(double *state, double *unused, double *out_2244568362031364891) {
   out_2244568362031364891[0] = 0;
   out_2244568362031364891[1] = 0;
   out_2244568362031364891[2] = 0;
   out_2244568362031364891[3] = 0;
   out_2244568362031364891[4] = 1;
   out_2244568362031364891[5] = 0;
   out_2244568362031364891[6] = 0;
   out_2244568362031364891[7] = 0;
   out_2244568362031364891[8] = 0;
}
void h_26(double *state, double *unused, double *out_2192696010676609843) {
   out_2192696010676609843[0] = state[7];
}
void H_26(double *state, double *unused, double *out_5543982051312513746) {
   out_5543982051312513746[0] = 0;
   out_5543982051312513746[1] = 0;
   out_5543982051312513746[2] = 0;
   out_5543982051312513746[3] = 0;
   out_5543982051312513746[4] = 0;
   out_5543982051312513746[5] = 0;
   out_5543982051312513746[6] = 0;
   out_5543982051312513746[7] = 1;
   out_5543982051312513746[8] = 0;
}
void h_27(double *state, double *unused, double *out_6396221351931905454) {
   out_6396221351931905454[0] = state[3];
}
void H_27(double *state, double *unused, double *out_4419331673831789802) {
   out_4419331673831789802[0] = 0;
   out_4419331673831789802[1] = 0;
   out_4419331673831789802[2] = 0;
   out_4419331673831789802[3] = 1;
   out_4419331673831789802[4] = 0;
   out_4419331673831789802[5] = 0;
   out_4419331673831789802[6] = 0;
   out_4419331673831789802[7] = 0;
   out_4419331673831789802[8] = 0;
}
void h_29(double *state, double *unused, double *out_191606574544389709) {
   out_191606574544389709[0] = state[1];
}
void H_29(double *state, double *unused, double *out_1734337017716972707) {
   out_1734337017716972707[0] = 0;
   out_1734337017716972707[1] = 1;
   out_1734337017716972707[2] = 0;
   out_1734337017716972707[3] = 0;
   out_1734337017716972707[4] = 0;
   out_1734337017716972707[5] = 0;
   out_1734337017716972707[6] = 0;
   out_1734337017716972707[7] = 0;
   out_1734337017716972707[8] = 0;
}
void h_28(double *state, double *unused, double *out_293701916198711064) {
   out_293701916198711064[0] = state[0];
}
void H_28(double *state, double *unused, double *out_7231650655938680207) {
   out_7231650655938680207[0] = 1;
   out_7231650655938680207[1] = 0;
   out_7231650655938680207[2] = 0;
   out_7231650655938680207[3] = 0;
   out_7231650655938680207[4] = 0;
   out_7231650655938680207[5] = 0;
   out_7231650655938680207[6] = 0;
   out_7231650655938680207[7] = 0;
   out_7231650655938680207[8] = 0;
}
void h_31(double *state, double *unused, double *out_3411399925862778167) {
   out_3411399925862778167[0] = state[8];
}
void H_31(double *state, double *unused, double *out_9130612741646021218) {
   out_9130612741646021218[0] = 0;
   out_9130612741646021218[1] = 0;
   out_9130612741646021218[2] = 0;
   out_9130612741646021218[3] = 0;
   out_9130612741646021218[4] = 0;
   out_9130612741646021218[5] = 0;
   out_9130612741646021218[6] = 0;
   out_9130612741646021218[7] = 0;
   out_9130612741646021218[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_2901723881323854107) {
  err_fun(nom_x, delta_x, out_2901723881323854107);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_2131234716339310483) {
  inv_err_fun(nom_x, true_x, out_2131234716339310483);
}
void car_H_mod_fun(double *state, double *out_796115697957996727) {
  H_mod_fun(state, out_796115697957996727);
}
void car_f_fun(double *state, double dt, double *out_1948741695251664277) {
  f_fun(state,  dt, out_1948741695251664277);
}
void car_F_fun(double *state, double dt, double *out_8655261788612512074) {
  F_fun(state,  dt, out_8655261788612512074);
}
void car_h_25(double *state, double *unused, double *out_3359435300487572769) {
  h_25(state, unused, out_3359435300487572769);
}
void car_H_25(double *state, double *unused, double *out_9161258703522981646) {
  H_25(state, unused, out_9161258703522981646);
}
void car_h_24(double *state, double *unused, double *out_6622515166733284665) {
  h_24(state, unused, out_6622515166733284665);
}
void car_H_24(double *state, double *unused, double *out_8316262094739286247) {
  H_24(state, unused, out_8316262094739286247);
}
void car_h_30(double *state, double *unused, double *out_411709310132087808) {
  h_30(state, unused, out_411709310132087808);
}
void car_H_30(double *state, double *unused, double *out_2244568362031364891) {
  H_30(state, unused, out_2244568362031364891);
}
void car_h_26(double *state, double *unused, double *out_2192696010676609843) {
  h_26(state, unused, out_2192696010676609843);
}
void car_H_26(double *state, double *unused, double *out_5543982051312513746) {
  H_26(state, unused, out_5543982051312513746);
}
void car_h_27(double *state, double *unused, double *out_6396221351931905454) {
  h_27(state, unused, out_6396221351931905454);
}
void car_H_27(double *state, double *unused, double *out_4419331673831789802) {
  H_27(state, unused, out_4419331673831789802);
}
void car_h_29(double *state, double *unused, double *out_191606574544389709) {
  h_29(state, unused, out_191606574544389709);
}
void car_H_29(double *state, double *unused, double *out_1734337017716972707) {
  H_29(state, unused, out_1734337017716972707);
}
void car_h_28(double *state, double *unused, double *out_293701916198711064) {
  h_28(state, unused, out_293701916198711064);
}
void car_H_28(double *state, double *unused, double *out_7231650655938680207) {
  H_28(state, unused, out_7231650655938680207);
}
void car_h_31(double *state, double *unused, double *out_3411399925862778167) {
  h_31(state, unused, out_3411399925862778167);
}
void car_H_31(double *state, double *unused, double *out_9130612741646021218) {
  H_31(state, unused, out_9130612741646021218);
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
