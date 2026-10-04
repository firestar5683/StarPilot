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
void err_fun(double *nom_x, double *delta_x, double *out_4009510058988412331) {
   out_4009510058988412331[0] = delta_x[0] + nom_x[0];
   out_4009510058988412331[1] = delta_x[1] + nom_x[1];
   out_4009510058988412331[2] = delta_x[2] + nom_x[2];
   out_4009510058988412331[3] = delta_x[3] + nom_x[3];
   out_4009510058988412331[4] = delta_x[4] + nom_x[4];
   out_4009510058988412331[5] = delta_x[5] + nom_x[5];
   out_4009510058988412331[6] = delta_x[6] + nom_x[6];
   out_4009510058988412331[7] = delta_x[7] + nom_x[7];
   out_4009510058988412331[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_211208841364349865) {
   out_211208841364349865[0] = -nom_x[0] + true_x[0];
   out_211208841364349865[1] = -nom_x[1] + true_x[1];
   out_211208841364349865[2] = -nom_x[2] + true_x[2];
   out_211208841364349865[3] = -nom_x[3] + true_x[3];
   out_211208841364349865[4] = -nom_x[4] + true_x[4];
   out_211208841364349865[5] = -nom_x[5] + true_x[5];
   out_211208841364349865[6] = -nom_x[6] + true_x[6];
   out_211208841364349865[7] = -nom_x[7] + true_x[7];
   out_211208841364349865[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_8439691916014613669) {
   out_8439691916014613669[0] = 1.0;
   out_8439691916014613669[1] = 0.0;
   out_8439691916014613669[2] = 0.0;
   out_8439691916014613669[3] = 0.0;
   out_8439691916014613669[4] = 0.0;
   out_8439691916014613669[5] = 0.0;
   out_8439691916014613669[6] = 0.0;
   out_8439691916014613669[7] = 0.0;
   out_8439691916014613669[8] = 0.0;
   out_8439691916014613669[9] = 0.0;
   out_8439691916014613669[10] = 1.0;
   out_8439691916014613669[11] = 0.0;
   out_8439691916014613669[12] = 0.0;
   out_8439691916014613669[13] = 0.0;
   out_8439691916014613669[14] = 0.0;
   out_8439691916014613669[15] = 0.0;
   out_8439691916014613669[16] = 0.0;
   out_8439691916014613669[17] = 0.0;
   out_8439691916014613669[18] = 0.0;
   out_8439691916014613669[19] = 0.0;
   out_8439691916014613669[20] = 1.0;
   out_8439691916014613669[21] = 0.0;
   out_8439691916014613669[22] = 0.0;
   out_8439691916014613669[23] = 0.0;
   out_8439691916014613669[24] = 0.0;
   out_8439691916014613669[25] = 0.0;
   out_8439691916014613669[26] = 0.0;
   out_8439691916014613669[27] = 0.0;
   out_8439691916014613669[28] = 0.0;
   out_8439691916014613669[29] = 0.0;
   out_8439691916014613669[30] = 1.0;
   out_8439691916014613669[31] = 0.0;
   out_8439691916014613669[32] = 0.0;
   out_8439691916014613669[33] = 0.0;
   out_8439691916014613669[34] = 0.0;
   out_8439691916014613669[35] = 0.0;
   out_8439691916014613669[36] = 0.0;
   out_8439691916014613669[37] = 0.0;
   out_8439691916014613669[38] = 0.0;
   out_8439691916014613669[39] = 0.0;
   out_8439691916014613669[40] = 1.0;
   out_8439691916014613669[41] = 0.0;
   out_8439691916014613669[42] = 0.0;
   out_8439691916014613669[43] = 0.0;
   out_8439691916014613669[44] = 0.0;
   out_8439691916014613669[45] = 0.0;
   out_8439691916014613669[46] = 0.0;
   out_8439691916014613669[47] = 0.0;
   out_8439691916014613669[48] = 0.0;
   out_8439691916014613669[49] = 0.0;
   out_8439691916014613669[50] = 1.0;
   out_8439691916014613669[51] = 0.0;
   out_8439691916014613669[52] = 0.0;
   out_8439691916014613669[53] = 0.0;
   out_8439691916014613669[54] = 0.0;
   out_8439691916014613669[55] = 0.0;
   out_8439691916014613669[56] = 0.0;
   out_8439691916014613669[57] = 0.0;
   out_8439691916014613669[58] = 0.0;
   out_8439691916014613669[59] = 0.0;
   out_8439691916014613669[60] = 1.0;
   out_8439691916014613669[61] = 0.0;
   out_8439691916014613669[62] = 0.0;
   out_8439691916014613669[63] = 0.0;
   out_8439691916014613669[64] = 0.0;
   out_8439691916014613669[65] = 0.0;
   out_8439691916014613669[66] = 0.0;
   out_8439691916014613669[67] = 0.0;
   out_8439691916014613669[68] = 0.0;
   out_8439691916014613669[69] = 0.0;
   out_8439691916014613669[70] = 1.0;
   out_8439691916014613669[71] = 0.0;
   out_8439691916014613669[72] = 0.0;
   out_8439691916014613669[73] = 0.0;
   out_8439691916014613669[74] = 0.0;
   out_8439691916014613669[75] = 0.0;
   out_8439691916014613669[76] = 0.0;
   out_8439691916014613669[77] = 0.0;
   out_8439691916014613669[78] = 0.0;
   out_8439691916014613669[79] = 0.0;
   out_8439691916014613669[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_2756758349190389597) {
   out_2756758349190389597[0] = state[0];
   out_2756758349190389597[1] = state[1];
   out_2756758349190389597[2] = state[2];
   out_2756758349190389597[3] = state[3];
   out_2756758349190389597[4] = state[4];
   out_2756758349190389597[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_2756758349190389597[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_2756758349190389597[7] = state[7];
   out_2756758349190389597[8] = state[8];
}
void F_fun(double *state, double dt, double *out_6650625153394168514) {
   out_6650625153394168514[0] = 1;
   out_6650625153394168514[1] = 0;
   out_6650625153394168514[2] = 0;
   out_6650625153394168514[3] = 0;
   out_6650625153394168514[4] = 0;
   out_6650625153394168514[5] = 0;
   out_6650625153394168514[6] = 0;
   out_6650625153394168514[7] = 0;
   out_6650625153394168514[8] = 0;
   out_6650625153394168514[9] = 0;
   out_6650625153394168514[10] = 1;
   out_6650625153394168514[11] = 0;
   out_6650625153394168514[12] = 0;
   out_6650625153394168514[13] = 0;
   out_6650625153394168514[14] = 0;
   out_6650625153394168514[15] = 0;
   out_6650625153394168514[16] = 0;
   out_6650625153394168514[17] = 0;
   out_6650625153394168514[18] = 0;
   out_6650625153394168514[19] = 0;
   out_6650625153394168514[20] = 1;
   out_6650625153394168514[21] = 0;
   out_6650625153394168514[22] = 0;
   out_6650625153394168514[23] = 0;
   out_6650625153394168514[24] = 0;
   out_6650625153394168514[25] = 0;
   out_6650625153394168514[26] = 0;
   out_6650625153394168514[27] = 0;
   out_6650625153394168514[28] = 0;
   out_6650625153394168514[29] = 0;
   out_6650625153394168514[30] = 1;
   out_6650625153394168514[31] = 0;
   out_6650625153394168514[32] = 0;
   out_6650625153394168514[33] = 0;
   out_6650625153394168514[34] = 0;
   out_6650625153394168514[35] = 0;
   out_6650625153394168514[36] = 0;
   out_6650625153394168514[37] = 0;
   out_6650625153394168514[38] = 0;
   out_6650625153394168514[39] = 0;
   out_6650625153394168514[40] = 1;
   out_6650625153394168514[41] = 0;
   out_6650625153394168514[42] = 0;
   out_6650625153394168514[43] = 0;
   out_6650625153394168514[44] = 0;
   out_6650625153394168514[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_6650625153394168514[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_6650625153394168514[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_6650625153394168514[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_6650625153394168514[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_6650625153394168514[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_6650625153394168514[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_6650625153394168514[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_6650625153394168514[53] = -9.8100000000000005*dt;
   out_6650625153394168514[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_6650625153394168514[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_6650625153394168514[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_6650625153394168514[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_6650625153394168514[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_6650625153394168514[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_6650625153394168514[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_6650625153394168514[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_6650625153394168514[62] = 0;
   out_6650625153394168514[63] = 0;
   out_6650625153394168514[64] = 0;
   out_6650625153394168514[65] = 0;
   out_6650625153394168514[66] = 0;
   out_6650625153394168514[67] = 0;
   out_6650625153394168514[68] = 0;
   out_6650625153394168514[69] = 0;
   out_6650625153394168514[70] = 1;
   out_6650625153394168514[71] = 0;
   out_6650625153394168514[72] = 0;
   out_6650625153394168514[73] = 0;
   out_6650625153394168514[74] = 0;
   out_6650625153394168514[75] = 0;
   out_6650625153394168514[76] = 0;
   out_6650625153394168514[77] = 0;
   out_6650625153394168514[78] = 0;
   out_6650625153394168514[79] = 0;
   out_6650625153394168514[80] = 1;
}
void h_25(double *state, double *unused, double *out_5235044060477467306) {
   out_5235044060477467306[0] = state[6];
}
void H_25(double *state, double *unused, double *out_3510029197804907996) {
   out_3510029197804907996[0] = 0;
   out_3510029197804907996[1] = 0;
   out_3510029197804907996[2] = 0;
   out_3510029197804907996[3] = 0;
   out_3510029197804907996[4] = 0;
   out_3510029197804907996[5] = 0;
   out_3510029197804907996[6] = 1;
   out_3510029197804907996[7] = 0;
   out_3510029197804907996[8] = 0;
}
void h_24(double *state, double *unused, double *out_8680530398976897528) {
   out_8680530398976897528[0] = state[4];
   out_8680530398976897528[1] = state[5];
}
void H_24(double *state, double *unused, double *out_1358785667222798856) {
   out_1358785667222798856[0] = 0;
   out_1358785667222798856[1] = 0;
   out_1358785667222798856[2] = 0;
   out_1358785667222798856[3] = 0;
   out_1358785667222798856[4] = 1;
   out_1358785667222798856[5] = 0;
   out_1358785667222798856[6] = 0;
   out_1358785667222798856[7] = 0;
   out_1358785667222798856[8] = 0;
   out_1358785667222798856[9] = 0;
   out_1358785667222798856[10] = 0;
   out_1358785667222798856[11] = 0;
   out_1358785667222798856[12] = 0;
   out_1358785667222798856[13] = 0;
   out_1358785667222798856[14] = 1;
   out_1358785667222798856[15] = 0;
   out_1358785667222798856[16] = 0;
   out_1358785667222798856[17] = 0;
}
void h_30(double *state, double *unused, double *out_8872493588731489656) {
   out_8872493588731489656[0] = state[4];
}
void H_30(double *state, double *unused, double *out_1017667132322700202) {
   out_1017667132322700202[0] = 0;
   out_1017667132322700202[1] = 0;
   out_1017667132322700202[2] = 0;
   out_1017667132322700202[3] = 0;
   out_1017667132322700202[4] = 1;
   out_1017667132322700202[5] = 0;
   out_1017667132322700202[6] = 0;
   out_1017667132322700202[7] = 0;
   out_1017667132322700202[8] = 0;
}
void h_26(double *state, double *unused, double *out_6537464433533729275) {
   out_6537464433533729275[0] = state[7];
}
void H_26(double *state, double *unused, double *out_231474121069148228) {
   out_231474121069148228[0] = 0;
   out_231474121069148228[1] = 0;
   out_231474121069148228[2] = 0;
   out_231474121069148228[3] = 0;
   out_231474121069148228[4] = 0;
   out_231474121069148228[5] = 0;
   out_231474121069148228[6] = 0;
   out_231474121069148228[7] = 1;
   out_231474121069148228[8] = 0;
}
void h_27(double *state, double *unused, double *out_6419457039600352531) {
   out_6419457039600352531[0] = state[3];
}
void H_27(double *state, double *unused, double *out_1205926938861243015) {
   out_1205926938861243015[0] = 0;
   out_1205926938861243015[1] = 0;
   out_1205926938861243015[2] = 0;
   out_1205926938861243015[3] = 1;
   out_1205926938861243015[4] = 0;
   out_1205926938861243015[5] = 0;
   out_1205926938861243015[6] = 0;
   out_1205926938861243015[7] = 0;
   out_1205926938861243015[8] = 0;
}
void h_29(double *state, double *unused, double *out_7182045753995808696) {
   out_7182045753995808696[0] = state[1];
}
void H_29(double *state, double *unused, double *out_507435788008308018) {
   out_507435788008308018[0] = 0;
   out_507435788008308018[1] = 1;
   out_507435788008308018[2] = 0;
   out_507435788008308018[3] = 0;
   out_507435788008308018[4] = 0;
   out_507435788008308018[5] = 0;
   out_507435788008308018[6] = 0;
   out_507435788008308018[7] = 0;
   out_507435788008308018[8] = 0;
}
void h_28(double *state, double *unused, double *out_651026969752255553) {
   out_651026969752255553[0] = state[0];
}
void H_28(double *state, double *unused, double *out_5589834805077838592) {
   out_5589834805077838592[0] = 1;
   out_5589834805077838592[1] = 0;
   out_5589834805077838592[2] = 0;
   out_5589834805077838592[3] = 0;
   out_5589834805077838592[4] = 0;
   out_5589834805077838592[5] = 0;
   out_5589834805077838592[6] = 0;
   out_5589834805077838592[7] = 0;
   out_5589834805077838592[8] = 0;
}
void h_31(double *state, double *unused, double *out_5089524236256812335) {
   out_5089524236256812335[0] = state[8];
}
void H_31(double *state, double *unused, double *out_3540675159681868424) {
   out_3540675159681868424[0] = 0;
   out_3540675159681868424[1] = 0;
   out_3540675159681868424[2] = 0;
   out_3540675159681868424[3] = 0;
   out_3540675159681868424[4] = 0;
   out_3540675159681868424[5] = 0;
   out_3540675159681868424[6] = 0;
   out_3540675159681868424[7] = 0;
   out_3540675159681868424[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_4009510058988412331) {
  err_fun(nom_x, delta_x, out_4009510058988412331);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_211208841364349865) {
  inv_err_fun(nom_x, true_x, out_211208841364349865);
}
void car_H_mod_fun(double *state, double *out_8439691916014613669) {
  H_mod_fun(state, out_8439691916014613669);
}
void car_f_fun(double *state, double dt, double *out_2756758349190389597) {
  f_fun(state,  dt, out_2756758349190389597);
}
void car_F_fun(double *state, double dt, double *out_6650625153394168514) {
  F_fun(state,  dt, out_6650625153394168514);
}
void car_h_25(double *state, double *unused, double *out_5235044060477467306) {
  h_25(state, unused, out_5235044060477467306);
}
void car_H_25(double *state, double *unused, double *out_3510029197804907996) {
  H_25(state, unused, out_3510029197804907996);
}
void car_h_24(double *state, double *unused, double *out_8680530398976897528) {
  h_24(state, unused, out_8680530398976897528);
}
void car_H_24(double *state, double *unused, double *out_1358785667222798856) {
  H_24(state, unused, out_1358785667222798856);
}
void car_h_30(double *state, double *unused, double *out_8872493588731489656) {
  h_30(state, unused, out_8872493588731489656);
}
void car_H_30(double *state, double *unused, double *out_1017667132322700202) {
  H_30(state, unused, out_1017667132322700202);
}
void car_h_26(double *state, double *unused, double *out_6537464433533729275) {
  h_26(state, unused, out_6537464433533729275);
}
void car_H_26(double *state, double *unused, double *out_231474121069148228) {
  H_26(state, unused, out_231474121069148228);
}
void car_h_27(double *state, double *unused, double *out_6419457039600352531) {
  h_27(state, unused, out_6419457039600352531);
}
void car_H_27(double *state, double *unused, double *out_1205926938861243015) {
  H_27(state, unused, out_1205926938861243015);
}
void car_h_29(double *state, double *unused, double *out_7182045753995808696) {
  h_29(state, unused, out_7182045753995808696);
}
void car_H_29(double *state, double *unused, double *out_507435788008308018) {
  H_29(state, unused, out_507435788008308018);
}
void car_h_28(double *state, double *unused, double *out_651026969752255553) {
  h_28(state, unused, out_651026969752255553);
}
void car_H_28(double *state, double *unused, double *out_5589834805077838592) {
  H_28(state, unused, out_5589834805077838592);
}
void car_h_31(double *state, double *unused, double *out_5089524236256812335) {
  h_31(state, unused, out_5089524236256812335);
}
void car_H_31(double *state, double *unused, double *out_3540675159681868424) {
  H_31(state, unused, out_3540675159681868424);
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
