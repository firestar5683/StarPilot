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
void err_fun(double *nom_x, double *delta_x, double *out_694062864366320957) {
   out_694062864366320957[0] = delta_x[0] + nom_x[0];
   out_694062864366320957[1] = delta_x[1] + nom_x[1];
   out_694062864366320957[2] = delta_x[2] + nom_x[2];
   out_694062864366320957[3] = delta_x[3] + nom_x[3];
   out_694062864366320957[4] = delta_x[4] + nom_x[4];
   out_694062864366320957[5] = delta_x[5] + nom_x[5];
   out_694062864366320957[6] = delta_x[6] + nom_x[6];
   out_694062864366320957[7] = delta_x[7] + nom_x[7];
   out_694062864366320957[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_7656216431051591408) {
   out_7656216431051591408[0] = -nom_x[0] + true_x[0];
   out_7656216431051591408[1] = -nom_x[1] + true_x[1];
   out_7656216431051591408[2] = -nom_x[2] + true_x[2];
   out_7656216431051591408[3] = -nom_x[3] + true_x[3];
   out_7656216431051591408[4] = -nom_x[4] + true_x[4];
   out_7656216431051591408[5] = -nom_x[5] + true_x[5];
   out_7656216431051591408[6] = -nom_x[6] + true_x[6];
   out_7656216431051591408[7] = -nom_x[7] + true_x[7];
   out_7656216431051591408[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_2454126163912067491) {
   out_2454126163912067491[0] = 1.0;
   out_2454126163912067491[1] = 0.0;
   out_2454126163912067491[2] = 0.0;
   out_2454126163912067491[3] = 0.0;
   out_2454126163912067491[4] = 0.0;
   out_2454126163912067491[5] = 0.0;
   out_2454126163912067491[6] = 0.0;
   out_2454126163912067491[7] = 0.0;
   out_2454126163912067491[8] = 0.0;
   out_2454126163912067491[9] = 0.0;
   out_2454126163912067491[10] = 1.0;
   out_2454126163912067491[11] = 0.0;
   out_2454126163912067491[12] = 0.0;
   out_2454126163912067491[13] = 0.0;
   out_2454126163912067491[14] = 0.0;
   out_2454126163912067491[15] = 0.0;
   out_2454126163912067491[16] = 0.0;
   out_2454126163912067491[17] = 0.0;
   out_2454126163912067491[18] = 0.0;
   out_2454126163912067491[19] = 0.0;
   out_2454126163912067491[20] = 1.0;
   out_2454126163912067491[21] = 0.0;
   out_2454126163912067491[22] = 0.0;
   out_2454126163912067491[23] = 0.0;
   out_2454126163912067491[24] = 0.0;
   out_2454126163912067491[25] = 0.0;
   out_2454126163912067491[26] = 0.0;
   out_2454126163912067491[27] = 0.0;
   out_2454126163912067491[28] = 0.0;
   out_2454126163912067491[29] = 0.0;
   out_2454126163912067491[30] = 1.0;
   out_2454126163912067491[31] = 0.0;
   out_2454126163912067491[32] = 0.0;
   out_2454126163912067491[33] = 0.0;
   out_2454126163912067491[34] = 0.0;
   out_2454126163912067491[35] = 0.0;
   out_2454126163912067491[36] = 0.0;
   out_2454126163912067491[37] = 0.0;
   out_2454126163912067491[38] = 0.0;
   out_2454126163912067491[39] = 0.0;
   out_2454126163912067491[40] = 1.0;
   out_2454126163912067491[41] = 0.0;
   out_2454126163912067491[42] = 0.0;
   out_2454126163912067491[43] = 0.0;
   out_2454126163912067491[44] = 0.0;
   out_2454126163912067491[45] = 0.0;
   out_2454126163912067491[46] = 0.0;
   out_2454126163912067491[47] = 0.0;
   out_2454126163912067491[48] = 0.0;
   out_2454126163912067491[49] = 0.0;
   out_2454126163912067491[50] = 1.0;
   out_2454126163912067491[51] = 0.0;
   out_2454126163912067491[52] = 0.0;
   out_2454126163912067491[53] = 0.0;
   out_2454126163912067491[54] = 0.0;
   out_2454126163912067491[55] = 0.0;
   out_2454126163912067491[56] = 0.0;
   out_2454126163912067491[57] = 0.0;
   out_2454126163912067491[58] = 0.0;
   out_2454126163912067491[59] = 0.0;
   out_2454126163912067491[60] = 1.0;
   out_2454126163912067491[61] = 0.0;
   out_2454126163912067491[62] = 0.0;
   out_2454126163912067491[63] = 0.0;
   out_2454126163912067491[64] = 0.0;
   out_2454126163912067491[65] = 0.0;
   out_2454126163912067491[66] = 0.0;
   out_2454126163912067491[67] = 0.0;
   out_2454126163912067491[68] = 0.0;
   out_2454126163912067491[69] = 0.0;
   out_2454126163912067491[70] = 1.0;
   out_2454126163912067491[71] = 0.0;
   out_2454126163912067491[72] = 0.0;
   out_2454126163912067491[73] = 0.0;
   out_2454126163912067491[74] = 0.0;
   out_2454126163912067491[75] = 0.0;
   out_2454126163912067491[76] = 0.0;
   out_2454126163912067491[77] = 0.0;
   out_2454126163912067491[78] = 0.0;
   out_2454126163912067491[79] = 0.0;
   out_2454126163912067491[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_1843607112126961388) {
   out_1843607112126961388[0] = state[0];
   out_1843607112126961388[1] = state[1];
   out_1843607112126961388[2] = state[2];
   out_1843607112126961388[3] = state[3];
   out_1843607112126961388[4] = state[4];
   out_1843607112126961388[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_1843607112126961388[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_1843607112126961388[7] = state[7];
   out_1843607112126961388[8] = state[8];
}
void F_fun(double *state, double dt, double *out_2182262497468252920) {
   out_2182262497468252920[0] = 1;
   out_2182262497468252920[1] = 0;
   out_2182262497468252920[2] = 0;
   out_2182262497468252920[3] = 0;
   out_2182262497468252920[4] = 0;
   out_2182262497468252920[5] = 0;
   out_2182262497468252920[6] = 0;
   out_2182262497468252920[7] = 0;
   out_2182262497468252920[8] = 0;
   out_2182262497468252920[9] = 0;
   out_2182262497468252920[10] = 1;
   out_2182262497468252920[11] = 0;
   out_2182262497468252920[12] = 0;
   out_2182262497468252920[13] = 0;
   out_2182262497468252920[14] = 0;
   out_2182262497468252920[15] = 0;
   out_2182262497468252920[16] = 0;
   out_2182262497468252920[17] = 0;
   out_2182262497468252920[18] = 0;
   out_2182262497468252920[19] = 0;
   out_2182262497468252920[20] = 1;
   out_2182262497468252920[21] = 0;
   out_2182262497468252920[22] = 0;
   out_2182262497468252920[23] = 0;
   out_2182262497468252920[24] = 0;
   out_2182262497468252920[25] = 0;
   out_2182262497468252920[26] = 0;
   out_2182262497468252920[27] = 0;
   out_2182262497468252920[28] = 0;
   out_2182262497468252920[29] = 0;
   out_2182262497468252920[30] = 1;
   out_2182262497468252920[31] = 0;
   out_2182262497468252920[32] = 0;
   out_2182262497468252920[33] = 0;
   out_2182262497468252920[34] = 0;
   out_2182262497468252920[35] = 0;
   out_2182262497468252920[36] = 0;
   out_2182262497468252920[37] = 0;
   out_2182262497468252920[38] = 0;
   out_2182262497468252920[39] = 0;
   out_2182262497468252920[40] = 1;
   out_2182262497468252920[41] = 0;
   out_2182262497468252920[42] = 0;
   out_2182262497468252920[43] = 0;
   out_2182262497468252920[44] = 0;
   out_2182262497468252920[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_2182262497468252920[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_2182262497468252920[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_2182262497468252920[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_2182262497468252920[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_2182262497468252920[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_2182262497468252920[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_2182262497468252920[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_2182262497468252920[53] = -9.8100000000000005*dt;
   out_2182262497468252920[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_2182262497468252920[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_2182262497468252920[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_2182262497468252920[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_2182262497468252920[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_2182262497468252920[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_2182262497468252920[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_2182262497468252920[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_2182262497468252920[62] = 0;
   out_2182262497468252920[63] = 0;
   out_2182262497468252920[64] = 0;
   out_2182262497468252920[65] = 0;
   out_2182262497468252920[66] = 0;
   out_2182262497468252920[67] = 0;
   out_2182262497468252920[68] = 0;
   out_2182262497468252920[69] = 0;
   out_2182262497468252920[70] = 1;
   out_2182262497468252920[71] = 0;
   out_2182262497468252920[72] = 0;
   out_2182262497468252920[73] = 0;
   out_2182262497468252920[74] = 0;
   out_2182262497468252920[75] = 0;
   out_2182262497468252920[76] = 0;
   out_2182262497468252920[77] = 0;
   out_2182262497468252920[78] = 0;
   out_2182262497468252920[79] = 0;
   out_2182262497468252920[80] = 1;
}
void h_25(double *state, double *unused, double *out_4798003278786560335) {
   out_4798003278786560335[0] = state[6];
}
void H_25(double *state, double *unused, double *out_7357817989096732331) {
   out_7357817989096732331[0] = 0;
   out_7357817989096732331[1] = 0;
   out_7357817989096732331[2] = 0;
   out_7357817989096732331[3] = 0;
   out_7357817989096732331[4] = 0;
   out_7357817989096732331[5] = 0;
   out_7357817989096732331[6] = 1;
   out_7357817989096732331[7] = 0;
   out_7357817989096732331[8] = 0;
}
void h_24(double *state, double *unused, double *out_6970490004472512085) {
   out_6970490004472512085[0] = state[4];
   out_6970490004472512085[1] = state[5];
}
void H_24(double *state, double *unused, double *out_1156785309245570905) {
   out_1156785309245570905[0] = 0;
   out_1156785309245570905[1] = 0;
   out_1156785309245570905[2] = 0;
   out_1156785309245570905[3] = 0;
   out_1156785309245570905[4] = 1;
   out_1156785309245570905[5] = 0;
   out_1156785309245570905[6] = 0;
   out_1156785309245570905[7] = 0;
   out_1156785309245570905[8] = 0;
   out_1156785309245570905[9] = 0;
   out_1156785309245570905[10] = 0;
   out_1156785309245570905[11] = 0;
   out_1156785309245570905[12] = 0;
   out_1156785309245570905[13] = 0;
   out_1156785309245570905[14] = 1;
   out_1156785309245570905[15] = 0;
   out_1156785309245570905[16] = 0;
   out_1156785309245570905[17] = 0;
}
void h_30(double *state, double *unused, double *out_3972351172998717479) {
   out_3972351172998717479[0] = state[4];
}
void H_30(double *state, double *unused, double *out_7228479041953492261) {
   out_7228479041953492261[0] = 0;
   out_7228479041953492261[1] = 0;
   out_7228479041953492261[2] = 0;
   out_7228479041953492261[3] = 0;
   out_7228479041953492261[4] = 1;
   out_7228479041953492261[5] = 0;
   out_7228479041953492261[6] = 0;
   out_7228479041953492261[7] = 0;
   out_7228479041953492261[8] = 0;
}
void h_26(double *state, double *unused, double *out_1029322094662128166) {
   out_1029322094662128166[0] = state[7];
}
void H_26(double *state, double *unused, double *out_3616314670222676107) {
   out_3616314670222676107[0] = 0;
   out_3616314670222676107[1] = 0;
   out_3616314670222676107[2] = 0;
   out_3616314670222676107[3] = 0;
   out_3616314670222676107[4] = 0;
   out_3616314670222676107[5] = 0;
   out_3616314670222676107[6] = 0;
   out_3616314670222676107[7] = 1;
   out_3616314670222676107[8] = 0;
}
void h_27(double *state, double *unused, double *out_9195955360068189347) {
   out_9195955360068189347[0] = state[3];
}
void H_27(double *state, double *unused, double *out_5053715730153067350) {
   out_5053715730153067350[0] = 0;
   out_5053715730153067350[1] = 0;
   out_5053715730153067350[2] = 0;
   out_5053715730153067350[3] = 1;
   out_5053715730153067350[4] = 0;
   out_5053715730153067350[5] = 0;
   out_5053715730153067350[6] = 0;
   out_5053715730153067350[7] = 0;
   out_5053715730153067350[8] = 0;
}
void h_29(double *state, double *unused, double *out_9038768691717060202) {
   out_9038768691717060202[0] = state[1];
}
void H_29(double *state, double *unused, double *out_3340353003283516317) {
   out_3340353003283516317[0] = 0;
   out_3340353003283516317[1] = 1;
   out_3340353003283516317[2] = 0;
   out_3340353003283516317[3] = 0;
   out_3340353003283516317[4] = 0;
   out_3340353003283516317[5] = 0;
   out_3340353003283516317[6] = 0;
   out_3340353003283516317[7] = 0;
   out_3340353003283516317[8] = 0;
}
void h_28(double *state, double *unused, double *out_4249115445980516624) {
   out_4249115445980516624[0] = state[0];
}
void H_28(double *state, double *unused, double *out_5303983274848842568) {
   out_5303983274848842568[0] = 1;
   out_5303983274848842568[1] = 0;
   out_5303983274848842568[2] = 0;
   out_5303983274848842568[3] = 0;
   out_5303983274848842568[4] = 0;
   out_5303983274848842568[5] = 0;
   out_5303983274848842568[6] = 0;
   out_5303983274848842568[7] = 0;
   out_5303983274848842568[8] = 0;
}
void h_31(double *state, double *unused, double *out_5644913485036226869) {
   out_5644913485036226869[0] = state[8];
}
void H_31(double *state, double *unused, double *out_7388463950973692759) {
   out_7388463950973692759[0] = 0;
   out_7388463950973692759[1] = 0;
   out_7388463950973692759[2] = 0;
   out_7388463950973692759[3] = 0;
   out_7388463950973692759[4] = 0;
   out_7388463950973692759[5] = 0;
   out_7388463950973692759[6] = 0;
   out_7388463950973692759[7] = 0;
   out_7388463950973692759[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_694062864366320957) {
  err_fun(nom_x, delta_x, out_694062864366320957);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_7656216431051591408) {
  inv_err_fun(nom_x, true_x, out_7656216431051591408);
}
void car_H_mod_fun(double *state, double *out_2454126163912067491) {
  H_mod_fun(state, out_2454126163912067491);
}
void car_f_fun(double *state, double dt, double *out_1843607112126961388) {
  f_fun(state,  dt, out_1843607112126961388);
}
void car_F_fun(double *state, double dt, double *out_2182262497468252920) {
  F_fun(state,  dt, out_2182262497468252920);
}
void car_h_25(double *state, double *unused, double *out_4798003278786560335) {
  h_25(state, unused, out_4798003278786560335);
}
void car_H_25(double *state, double *unused, double *out_7357817989096732331) {
  H_25(state, unused, out_7357817989096732331);
}
void car_h_24(double *state, double *unused, double *out_6970490004472512085) {
  h_24(state, unused, out_6970490004472512085);
}
void car_H_24(double *state, double *unused, double *out_1156785309245570905) {
  H_24(state, unused, out_1156785309245570905);
}
void car_h_30(double *state, double *unused, double *out_3972351172998717479) {
  h_30(state, unused, out_3972351172998717479);
}
void car_H_30(double *state, double *unused, double *out_7228479041953492261) {
  H_30(state, unused, out_7228479041953492261);
}
void car_h_26(double *state, double *unused, double *out_1029322094662128166) {
  h_26(state, unused, out_1029322094662128166);
}
void car_H_26(double *state, double *unused, double *out_3616314670222676107) {
  H_26(state, unused, out_3616314670222676107);
}
void car_h_27(double *state, double *unused, double *out_9195955360068189347) {
  h_27(state, unused, out_9195955360068189347);
}
void car_H_27(double *state, double *unused, double *out_5053715730153067350) {
  H_27(state, unused, out_5053715730153067350);
}
void car_h_29(double *state, double *unused, double *out_9038768691717060202) {
  h_29(state, unused, out_9038768691717060202);
}
void car_H_29(double *state, double *unused, double *out_3340353003283516317) {
  H_29(state, unused, out_3340353003283516317);
}
void car_h_28(double *state, double *unused, double *out_4249115445980516624) {
  h_28(state, unused, out_4249115445980516624);
}
void car_H_28(double *state, double *unused, double *out_5303983274848842568) {
  H_28(state, unused, out_5303983274848842568);
}
void car_h_31(double *state, double *unused, double *out_5644913485036226869) {
  h_31(state, unused, out_5644913485036226869);
}
void car_H_31(double *state, double *unused, double *out_7388463950973692759) {
  H_31(state, unused, out_7388463950973692759);
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
