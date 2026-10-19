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
void err_fun(double *nom_x, double *delta_x, double *out_8346173601194974305) {
   out_8346173601194974305[0] = delta_x[0] + nom_x[0];
   out_8346173601194974305[1] = delta_x[1] + nom_x[1];
   out_8346173601194974305[2] = delta_x[2] + nom_x[2];
   out_8346173601194974305[3] = delta_x[3] + nom_x[3];
   out_8346173601194974305[4] = delta_x[4] + nom_x[4];
   out_8346173601194974305[5] = delta_x[5] + nom_x[5];
   out_8346173601194974305[6] = delta_x[6] + nom_x[6];
   out_8346173601194974305[7] = delta_x[7] + nom_x[7];
   out_8346173601194974305[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_5160097127653636741) {
   out_5160097127653636741[0] = -nom_x[0] + true_x[0];
   out_5160097127653636741[1] = -nom_x[1] + true_x[1];
   out_5160097127653636741[2] = -nom_x[2] + true_x[2];
   out_5160097127653636741[3] = -nom_x[3] + true_x[3];
   out_5160097127653636741[4] = -nom_x[4] + true_x[4];
   out_5160097127653636741[5] = -nom_x[5] + true_x[5];
   out_5160097127653636741[6] = -nom_x[6] + true_x[6];
   out_5160097127653636741[7] = -nom_x[7] + true_x[7];
   out_5160097127653636741[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_5363774524485386634) {
   out_5363774524485386634[0] = 1.0;
   out_5363774524485386634[1] = 0.0;
   out_5363774524485386634[2] = 0.0;
   out_5363774524485386634[3] = 0.0;
   out_5363774524485386634[4] = 0.0;
   out_5363774524485386634[5] = 0.0;
   out_5363774524485386634[6] = 0.0;
   out_5363774524485386634[7] = 0.0;
   out_5363774524485386634[8] = 0.0;
   out_5363774524485386634[9] = 0.0;
   out_5363774524485386634[10] = 1.0;
   out_5363774524485386634[11] = 0.0;
   out_5363774524485386634[12] = 0.0;
   out_5363774524485386634[13] = 0.0;
   out_5363774524485386634[14] = 0.0;
   out_5363774524485386634[15] = 0.0;
   out_5363774524485386634[16] = 0.0;
   out_5363774524485386634[17] = 0.0;
   out_5363774524485386634[18] = 0.0;
   out_5363774524485386634[19] = 0.0;
   out_5363774524485386634[20] = 1.0;
   out_5363774524485386634[21] = 0.0;
   out_5363774524485386634[22] = 0.0;
   out_5363774524485386634[23] = 0.0;
   out_5363774524485386634[24] = 0.0;
   out_5363774524485386634[25] = 0.0;
   out_5363774524485386634[26] = 0.0;
   out_5363774524485386634[27] = 0.0;
   out_5363774524485386634[28] = 0.0;
   out_5363774524485386634[29] = 0.0;
   out_5363774524485386634[30] = 1.0;
   out_5363774524485386634[31] = 0.0;
   out_5363774524485386634[32] = 0.0;
   out_5363774524485386634[33] = 0.0;
   out_5363774524485386634[34] = 0.0;
   out_5363774524485386634[35] = 0.0;
   out_5363774524485386634[36] = 0.0;
   out_5363774524485386634[37] = 0.0;
   out_5363774524485386634[38] = 0.0;
   out_5363774524485386634[39] = 0.0;
   out_5363774524485386634[40] = 1.0;
   out_5363774524485386634[41] = 0.0;
   out_5363774524485386634[42] = 0.0;
   out_5363774524485386634[43] = 0.0;
   out_5363774524485386634[44] = 0.0;
   out_5363774524485386634[45] = 0.0;
   out_5363774524485386634[46] = 0.0;
   out_5363774524485386634[47] = 0.0;
   out_5363774524485386634[48] = 0.0;
   out_5363774524485386634[49] = 0.0;
   out_5363774524485386634[50] = 1.0;
   out_5363774524485386634[51] = 0.0;
   out_5363774524485386634[52] = 0.0;
   out_5363774524485386634[53] = 0.0;
   out_5363774524485386634[54] = 0.0;
   out_5363774524485386634[55] = 0.0;
   out_5363774524485386634[56] = 0.0;
   out_5363774524485386634[57] = 0.0;
   out_5363774524485386634[58] = 0.0;
   out_5363774524485386634[59] = 0.0;
   out_5363774524485386634[60] = 1.0;
   out_5363774524485386634[61] = 0.0;
   out_5363774524485386634[62] = 0.0;
   out_5363774524485386634[63] = 0.0;
   out_5363774524485386634[64] = 0.0;
   out_5363774524485386634[65] = 0.0;
   out_5363774524485386634[66] = 0.0;
   out_5363774524485386634[67] = 0.0;
   out_5363774524485386634[68] = 0.0;
   out_5363774524485386634[69] = 0.0;
   out_5363774524485386634[70] = 1.0;
   out_5363774524485386634[71] = 0.0;
   out_5363774524485386634[72] = 0.0;
   out_5363774524485386634[73] = 0.0;
   out_5363774524485386634[74] = 0.0;
   out_5363774524485386634[75] = 0.0;
   out_5363774524485386634[76] = 0.0;
   out_5363774524485386634[77] = 0.0;
   out_5363774524485386634[78] = 0.0;
   out_5363774524485386634[79] = 0.0;
   out_5363774524485386634[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_1540318947581584736) {
   out_1540318947581584736[0] = state[0];
   out_1540318947581584736[1] = state[1];
   out_1540318947581584736[2] = state[2];
   out_1540318947581584736[3] = state[3];
   out_1540318947581584736[4] = state[4];
   out_1540318947581584736[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_1540318947581584736[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_1540318947581584736[7] = state[7];
   out_1540318947581584736[8] = state[8];
}
void F_fun(double *state, double dt, double *out_7934222883812967780) {
   out_7934222883812967780[0] = 1;
   out_7934222883812967780[1] = 0;
   out_7934222883812967780[2] = 0;
   out_7934222883812967780[3] = 0;
   out_7934222883812967780[4] = 0;
   out_7934222883812967780[5] = 0;
   out_7934222883812967780[6] = 0;
   out_7934222883812967780[7] = 0;
   out_7934222883812967780[8] = 0;
   out_7934222883812967780[9] = 0;
   out_7934222883812967780[10] = 1;
   out_7934222883812967780[11] = 0;
   out_7934222883812967780[12] = 0;
   out_7934222883812967780[13] = 0;
   out_7934222883812967780[14] = 0;
   out_7934222883812967780[15] = 0;
   out_7934222883812967780[16] = 0;
   out_7934222883812967780[17] = 0;
   out_7934222883812967780[18] = 0;
   out_7934222883812967780[19] = 0;
   out_7934222883812967780[20] = 1;
   out_7934222883812967780[21] = 0;
   out_7934222883812967780[22] = 0;
   out_7934222883812967780[23] = 0;
   out_7934222883812967780[24] = 0;
   out_7934222883812967780[25] = 0;
   out_7934222883812967780[26] = 0;
   out_7934222883812967780[27] = 0;
   out_7934222883812967780[28] = 0;
   out_7934222883812967780[29] = 0;
   out_7934222883812967780[30] = 1;
   out_7934222883812967780[31] = 0;
   out_7934222883812967780[32] = 0;
   out_7934222883812967780[33] = 0;
   out_7934222883812967780[34] = 0;
   out_7934222883812967780[35] = 0;
   out_7934222883812967780[36] = 0;
   out_7934222883812967780[37] = 0;
   out_7934222883812967780[38] = 0;
   out_7934222883812967780[39] = 0;
   out_7934222883812967780[40] = 1;
   out_7934222883812967780[41] = 0;
   out_7934222883812967780[42] = 0;
   out_7934222883812967780[43] = 0;
   out_7934222883812967780[44] = 0;
   out_7934222883812967780[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_7934222883812967780[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_7934222883812967780[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_7934222883812967780[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_7934222883812967780[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_7934222883812967780[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_7934222883812967780[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_7934222883812967780[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_7934222883812967780[53] = -9.8100000000000005*dt;
   out_7934222883812967780[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_7934222883812967780[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_7934222883812967780[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_7934222883812967780[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_7934222883812967780[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_7934222883812967780[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_7934222883812967780[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_7934222883812967780[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_7934222883812967780[62] = 0;
   out_7934222883812967780[63] = 0;
   out_7934222883812967780[64] = 0;
   out_7934222883812967780[65] = 0;
   out_7934222883812967780[66] = 0;
   out_7934222883812967780[67] = 0;
   out_7934222883812967780[68] = 0;
   out_7934222883812967780[69] = 0;
   out_7934222883812967780[70] = 1;
   out_7934222883812967780[71] = 0;
   out_7934222883812967780[72] = 0;
   out_7934222883812967780[73] = 0;
   out_7934222883812967780[74] = 0;
   out_7934222883812967780[75] = 0;
   out_7934222883812967780[76] = 0;
   out_7934222883812967780[77] = 0;
   out_7934222883812967780[78] = 0;
   out_7934222883812967780[79] = 0;
   out_7934222883812967780[80] = 1;
}
void h_25(double *state, double *unused, double *out_7598930903288826977) {
   out_7598930903288826977[0] = state[6];
}
void H_25(double *state, double *unused, double *out_460082699300721794) {
   out_460082699300721794[0] = 0;
   out_460082699300721794[1] = 0;
   out_460082699300721794[2] = 0;
   out_460082699300721794[3] = 0;
   out_460082699300721794[4] = 0;
   out_460082699300721794[5] = 0;
   out_460082699300721794[6] = 1;
   out_460082699300721794[7] = 0;
   out_460082699300721794[8] = 0;
}
void h_24(double *state, double *unused, double *out_5154566491491640288) {
   out_5154566491491640288[0] = state[4];
   out_5154566491491640288[1] = state[5];
}
void H_24(double *state, double *unused, double *out_6115489107290796307) {
   out_6115489107290796307[0] = 0;
   out_6115489107290796307[1] = 0;
   out_6115489107290796307[2] = 0;
   out_6115489107290796307[3] = 0;
   out_6115489107290796307[4] = 1;
   out_6115489107290796307[5] = 0;
   out_6115489107290796307[6] = 0;
   out_6115489107290796307[7] = 0;
   out_6115489107290796307[8] = 0;
   out_6115489107290796307[9] = 0;
   out_6115489107290796307[10] = 0;
   out_6115489107290796307[11] = 0;
   out_6115489107290796307[12] = 0;
   out_6115489107290796307[13] = 0;
   out_6115489107290796307[14] = 1;
   out_6115489107290796307[15] = 0;
   out_6115489107290796307[16] = 0;
   out_6115489107290796307[17] = 0;
}
void h_30(double *state, double *unused, double *out_6960167479500316175) {
   out_6960167479500316175[0] = state[4];
}
void H_30(double *state, double *unused, double *out_6456607642190894961) {
   out_6456607642190894961[0] = 0;
   out_6456607642190894961[1] = 0;
   out_6456607642190894961[2] = 0;
   out_6456607642190894961[3] = 0;
   out_6456607642190894961[4] = 1;
   out_6456607642190894961[5] = 0;
   out_6456607642190894961[6] = 0;
   out_6456607642190894961[7] = 0;
   out_6456607642190894961[8] = 0;
}
void h_26(double *state, double *unused, double *out_5087535076795386295) {
   out_5087535076795386295[0] = state[7];
}
void H_26(double *state, double *unused, double *out_2844443270460078807) {
   out_2844443270460078807[0] = 0;
   out_2844443270460078807[1] = 0;
   out_2844443270460078807[2] = 0;
   out_2844443270460078807[3] = 0;
   out_2844443270460078807[4] = 0;
   out_2844443270460078807[5] = 0;
   out_2844443270460078807[6] = 0;
   out_2844443270460078807[7] = 1;
   out_2844443270460078807[8] = 0;
}
void h_27(double *state, double *unused, double *out_4994525582480129326) {
   out_4994525582480129326[0] = state[3];
}
void H_27(double *state, double *unused, double *out_4281844330390470050) {
   out_4281844330390470050[0] = 0;
   out_4281844330390470050[1] = 0;
   out_4281844330390470050[2] = 0;
   out_4281844330390470050[3] = 1;
   out_4281844330390470050[4] = 0;
   out_4281844330390470050[5] = 0;
   out_4281844330390470050[6] = 0;
   out_4281844330390470050[7] = 0;
   out_4281844330390470050[8] = 0;
}
void h_29(double *state, double *unused, double *out_7296771295388762161) {
   out_7296771295388762161[0] = state[1];
}
void H_29(double *state, double *unused, double *out_6966838986505287145) {
   out_6966838986505287145[0] = 0;
   out_6966838986505287145[1] = 1;
   out_6966838986505287145[2] = 0;
   out_6966838986505287145[3] = 0;
   out_6966838986505287145[4] = 0;
   out_6966838986505287145[5] = 0;
   out_6966838986505287145[6] = 0;
   out_6966838986505287145[7] = 0;
   out_6966838986505287145[8] = 0;
}
void h_28(double *state, double *unused, double *out_6344779448990625368) {
   out_6344779448990625368[0] = state[0];
}
void H_28(double *state, double *unused, double *out_2513917413548611557) {
   out_2513917413548611557[0] = 1;
   out_2513917413548611557[1] = 0;
   out_2513917413548611557[2] = 0;
   out_2513917413548611557[3] = 0;
   out_2513917413548611557[4] = 0;
   out_2513917413548611557[5] = 0;
   out_2513917413548611557[6] = 0;
   out_2513917413548611557[7] = 0;
   out_2513917413548611557[8] = 0;
}
void h_31(double *state, double *unused, double *out_3644597213434738669) {
   out_3644597213434738669[0] = state[8];
}
void H_31(double *state, double *unused, double *out_6616592551211095459) {
   out_6616592551211095459[0] = 0;
   out_6616592551211095459[1] = 0;
   out_6616592551211095459[2] = 0;
   out_6616592551211095459[3] = 0;
   out_6616592551211095459[4] = 0;
   out_6616592551211095459[5] = 0;
   out_6616592551211095459[6] = 0;
   out_6616592551211095459[7] = 0;
   out_6616592551211095459[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_8346173601194974305) {
  err_fun(nom_x, delta_x, out_8346173601194974305);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_5160097127653636741) {
  inv_err_fun(nom_x, true_x, out_5160097127653636741);
}
void car_H_mod_fun(double *state, double *out_5363774524485386634) {
  H_mod_fun(state, out_5363774524485386634);
}
void car_f_fun(double *state, double dt, double *out_1540318947581584736) {
  f_fun(state,  dt, out_1540318947581584736);
}
void car_F_fun(double *state, double dt, double *out_7934222883812967780) {
  F_fun(state,  dt, out_7934222883812967780);
}
void car_h_25(double *state, double *unused, double *out_7598930903288826977) {
  h_25(state, unused, out_7598930903288826977);
}
void car_H_25(double *state, double *unused, double *out_460082699300721794) {
  H_25(state, unused, out_460082699300721794);
}
void car_h_24(double *state, double *unused, double *out_5154566491491640288) {
  h_24(state, unused, out_5154566491491640288);
}
void car_H_24(double *state, double *unused, double *out_6115489107290796307) {
  H_24(state, unused, out_6115489107290796307);
}
void car_h_30(double *state, double *unused, double *out_6960167479500316175) {
  h_30(state, unused, out_6960167479500316175);
}
void car_H_30(double *state, double *unused, double *out_6456607642190894961) {
  H_30(state, unused, out_6456607642190894961);
}
void car_h_26(double *state, double *unused, double *out_5087535076795386295) {
  h_26(state, unused, out_5087535076795386295);
}
void car_H_26(double *state, double *unused, double *out_2844443270460078807) {
  H_26(state, unused, out_2844443270460078807);
}
void car_h_27(double *state, double *unused, double *out_4994525582480129326) {
  h_27(state, unused, out_4994525582480129326);
}
void car_H_27(double *state, double *unused, double *out_4281844330390470050) {
  H_27(state, unused, out_4281844330390470050);
}
void car_h_29(double *state, double *unused, double *out_7296771295388762161) {
  h_29(state, unused, out_7296771295388762161);
}
void car_H_29(double *state, double *unused, double *out_6966838986505287145) {
  H_29(state, unused, out_6966838986505287145);
}
void car_h_28(double *state, double *unused, double *out_6344779448990625368) {
  h_28(state, unused, out_6344779448990625368);
}
void car_H_28(double *state, double *unused, double *out_2513917413548611557) {
  H_28(state, unused, out_2513917413548611557);
}
void car_h_31(double *state, double *unused, double *out_3644597213434738669) {
  h_31(state, unused, out_3644597213434738669);
}
void car_H_31(double *state, double *unused, double *out_6616592551211095459) {
  H_31(state, unused, out_6616592551211095459);
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
