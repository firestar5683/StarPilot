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
void err_fun(double *nom_x, double *delta_x, double *out_2633561206191248032) {
   out_2633561206191248032[0] = delta_x[0] + nom_x[0];
   out_2633561206191248032[1] = delta_x[1] + nom_x[1];
   out_2633561206191248032[2] = delta_x[2] + nom_x[2];
   out_2633561206191248032[3] = delta_x[3] + nom_x[3];
   out_2633561206191248032[4] = delta_x[4] + nom_x[4];
   out_2633561206191248032[5] = delta_x[5] + nom_x[5];
   out_2633561206191248032[6] = delta_x[6] + nom_x[6];
   out_2633561206191248032[7] = delta_x[7] + nom_x[7];
   out_2633561206191248032[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_5222322722539771080) {
   out_5222322722539771080[0] = -nom_x[0] + true_x[0];
   out_5222322722539771080[1] = -nom_x[1] + true_x[1];
   out_5222322722539771080[2] = -nom_x[2] + true_x[2];
   out_5222322722539771080[3] = -nom_x[3] + true_x[3];
   out_5222322722539771080[4] = -nom_x[4] + true_x[4];
   out_5222322722539771080[5] = -nom_x[5] + true_x[5];
   out_5222322722539771080[6] = -nom_x[6] + true_x[6];
   out_5222322722539771080[7] = -nom_x[7] + true_x[7];
   out_5222322722539771080[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_4733519652188373948) {
   out_4733519652188373948[0] = 1.0;
   out_4733519652188373948[1] = 0.0;
   out_4733519652188373948[2] = 0.0;
   out_4733519652188373948[3] = 0.0;
   out_4733519652188373948[4] = 0.0;
   out_4733519652188373948[5] = 0.0;
   out_4733519652188373948[6] = 0.0;
   out_4733519652188373948[7] = 0.0;
   out_4733519652188373948[8] = 0.0;
   out_4733519652188373948[9] = 0.0;
   out_4733519652188373948[10] = 1.0;
   out_4733519652188373948[11] = 0.0;
   out_4733519652188373948[12] = 0.0;
   out_4733519652188373948[13] = 0.0;
   out_4733519652188373948[14] = 0.0;
   out_4733519652188373948[15] = 0.0;
   out_4733519652188373948[16] = 0.0;
   out_4733519652188373948[17] = 0.0;
   out_4733519652188373948[18] = 0.0;
   out_4733519652188373948[19] = 0.0;
   out_4733519652188373948[20] = 1.0;
   out_4733519652188373948[21] = 0.0;
   out_4733519652188373948[22] = 0.0;
   out_4733519652188373948[23] = 0.0;
   out_4733519652188373948[24] = 0.0;
   out_4733519652188373948[25] = 0.0;
   out_4733519652188373948[26] = 0.0;
   out_4733519652188373948[27] = 0.0;
   out_4733519652188373948[28] = 0.0;
   out_4733519652188373948[29] = 0.0;
   out_4733519652188373948[30] = 1.0;
   out_4733519652188373948[31] = 0.0;
   out_4733519652188373948[32] = 0.0;
   out_4733519652188373948[33] = 0.0;
   out_4733519652188373948[34] = 0.0;
   out_4733519652188373948[35] = 0.0;
   out_4733519652188373948[36] = 0.0;
   out_4733519652188373948[37] = 0.0;
   out_4733519652188373948[38] = 0.0;
   out_4733519652188373948[39] = 0.0;
   out_4733519652188373948[40] = 1.0;
   out_4733519652188373948[41] = 0.0;
   out_4733519652188373948[42] = 0.0;
   out_4733519652188373948[43] = 0.0;
   out_4733519652188373948[44] = 0.0;
   out_4733519652188373948[45] = 0.0;
   out_4733519652188373948[46] = 0.0;
   out_4733519652188373948[47] = 0.0;
   out_4733519652188373948[48] = 0.0;
   out_4733519652188373948[49] = 0.0;
   out_4733519652188373948[50] = 1.0;
   out_4733519652188373948[51] = 0.0;
   out_4733519652188373948[52] = 0.0;
   out_4733519652188373948[53] = 0.0;
   out_4733519652188373948[54] = 0.0;
   out_4733519652188373948[55] = 0.0;
   out_4733519652188373948[56] = 0.0;
   out_4733519652188373948[57] = 0.0;
   out_4733519652188373948[58] = 0.0;
   out_4733519652188373948[59] = 0.0;
   out_4733519652188373948[60] = 1.0;
   out_4733519652188373948[61] = 0.0;
   out_4733519652188373948[62] = 0.0;
   out_4733519652188373948[63] = 0.0;
   out_4733519652188373948[64] = 0.0;
   out_4733519652188373948[65] = 0.0;
   out_4733519652188373948[66] = 0.0;
   out_4733519652188373948[67] = 0.0;
   out_4733519652188373948[68] = 0.0;
   out_4733519652188373948[69] = 0.0;
   out_4733519652188373948[70] = 1.0;
   out_4733519652188373948[71] = 0.0;
   out_4733519652188373948[72] = 0.0;
   out_4733519652188373948[73] = 0.0;
   out_4733519652188373948[74] = 0.0;
   out_4733519652188373948[75] = 0.0;
   out_4733519652188373948[76] = 0.0;
   out_4733519652188373948[77] = 0.0;
   out_4733519652188373948[78] = 0.0;
   out_4733519652188373948[79] = 0.0;
   out_4733519652188373948[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_9187320060872601910) {
   out_9187320060872601910[0] = state[0];
   out_9187320060872601910[1] = state[1];
   out_9187320060872601910[2] = state[2];
   out_9187320060872601910[3] = state[3];
   out_9187320060872601910[4] = state[4];
   out_9187320060872601910[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_9187320060872601910[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_9187320060872601910[7] = state[7];
   out_9187320060872601910[8] = state[8];
}
void F_fun(double *state, double dt, double *out_3219504763184105906) {
   out_3219504763184105906[0] = 1;
   out_3219504763184105906[1] = 0;
   out_3219504763184105906[2] = 0;
   out_3219504763184105906[3] = 0;
   out_3219504763184105906[4] = 0;
   out_3219504763184105906[5] = 0;
   out_3219504763184105906[6] = 0;
   out_3219504763184105906[7] = 0;
   out_3219504763184105906[8] = 0;
   out_3219504763184105906[9] = 0;
   out_3219504763184105906[10] = 1;
   out_3219504763184105906[11] = 0;
   out_3219504763184105906[12] = 0;
   out_3219504763184105906[13] = 0;
   out_3219504763184105906[14] = 0;
   out_3219504763184105906[15] = 0;
   out_3219504763184105906[16] = 0;
   out_3219504763184105906[17] = 0;
   out_3219504763184105906[18] = 0;
   out_3219504763184105906[19] = 0;
   out_3219504763184105906[20] = 1;
   out_3219504763184105906[21] = 0;
   out_3219504763184105906[22] = 0;
   out_3219504763184105906[23] = 0;
   out_3219504763184105906[24] = 0;
   out_3219504763184105906[25] = 0;
   out_3219504763184105906[26] = 0;
   out_3219504763184105906[27] = 0;
   out_3219504763184105906[28] = 0;
   out_3219504763184105906[29] = 0;
   out_3219504763184105906[30] = 1;
   out_3219504763184105906[31] = 0;
   out_3219504763184105906[32] = 0;
   out_3219504763184105906[33] = 0;
   out_3219504763184105906[34] = 0;
   out_3219504763184105906[35] = 0;
   out_3219504763184105906[36] = 0;
   out_3219504763184105906[37] = 0;
   out_3219504763184105906[38] = 0;
   out_3219504763184105906[39] = 0;
   out_3219504763184105906[40] = 1;
   out_3219504763184105906[41] = 0;
   out_3219504763184105906[42] = 0;
   out_3219504763184105906[43] = 0;
   out_3219504763184105906[44] = 0;
   out_3219504763184105906[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_3219504763184105906[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_3219504763184105906[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_3219504763184105906[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_3219504763184105906[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_3219504763184105906[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_3219504763184105906[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_3219504763184105906[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_3219504763184105906[53] = -9.8100000000000005*dt;
   out_3219504763184105906[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_3219504763184105906[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_3219504763184105906[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_3219504763184105906[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_3219504763184105906[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_3219504763184105906[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_3219504763184105906[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_3219504763184105906[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_3219504763184105906[62] = 0;
   out_3219504763184105906[63] = 0;
   out_3219504763184105906[64] = 0;
   out_3219504763184105906[65] = 0;
   out_3219504763184105906[66] = 0;
   out_3219504763184105906[67] = 0;
   out_3219504763184105906[68] = 0;
   out_3219504763184105906[69] = 0;
   out_3219504763184105906[70] = 1;
   out_3219504763184105906[71] = 0;
   out_3219504763184105906[72] = 0;
   out_3219504763184105906[73] = 0;
   out_3219504763184105906[74] = 0;
   out_3219504763184105906[75] = 0;
   out_3219504763184105906[76] = 0;
   out_3219504763184105906[77] = 0;
   out_3219504763184105906[78] = 0;
   out_3219504763184105906[79] = 0;
   out_3219504763184105906[80] = 1;
}
void h_25(double *state, double *unused, double *out_1821652184812404746) {
   out_1821652184812404746[0] = state[6];
}
void H_25(double *state, double *unused, double *out_4337363035662665471) {
   out_4337363035662665471[0] = 0;
   out_4337363035662665471[1] = 0;
   out_4337363035662665471[2] = 0;
   out_4337363035662665471[3] = 0;
   out_4337363035662665471[4] = 0;
   out_4337363035662665471[5] = 0;
   out_4337363035662665471[6] = 1;
   out_4337363035662665471[7] = 0;
   out_4337363035662665471[8] = 0;
}
void h_24(double *state, double *unused, double *out_258826568498121593) {
   out_258826568498121593[0] = state[4];
   out_258826568498121593[1] = state[5];
}
void H_24(double *state, double *unused, double *out_9206177900690372323) {
   out_9206177900690372323[0] = 0;
   out_9206177900690372323[1] = 0;
   out_9206177900690372323[2] = 0;
   out_9206177900690372323[3] = 0;
   out_9206177900690372323[4] = 1;
   out_9206177900690372323[5] = 0;
   out_9206177900690372323[6] = 0;
   out_9206177900690372323[7] = 0;
   out_9206177900690372323[8] = 0;
   out_9206177900690372323[9] = 0;
   out_9206177900690372323[10] = 0;
   out_9206177900690372323[11] = 0;
   out_9206177900690372323[12] = 0;
   out_9206177900690372323[13] = 0;
   out_9206177900690372323[14] = 1;
   out_9206177900690372323[15] = 0;
   out_9206177900690372323[16] = 0;
   out_9206177900690372323[17] = 0;
}
void h_30(double *state, double *unused, double *out_1546458122527898857) {
   out_1546458122527898857[0] = state[4];
}
void H_30(double *state, double *unused, double *out_8865059365790273669) {
   out_8865059365790273669[0] = 0;
   out_8865059365790273669[1] = 0;
   out_8865059365790273669[2] = 0;
   out_8865059365790273669[3] = 0;
   out_8865059365790273669[4] = 1;
   out_8865059365790273669[5] = 0;
   out_8865059365790273669[6] = 0;
   out_8865059365790273669[7] = 0;
   out_8865059365790273669[8] = 0;
}
void h_26(double *state, double *unused, double *out_4254367670776586025) {
   out_4254367670776586025[0] = state[7];
}
void H_26(double *state, double *unused, double *out_8078866354536721695) {
   out_8078866354536721695[0] = 0;
   out_8078866354536721695[1] = 0;
   out_8078866354536721695[2] = 0;
   out_8078866354536721695[3] = 0;
   out_8078866354536721695[4] = 0;
   out_8078866354536721695[5] = 0;
   out_8078866354536721695[6] = 0;
   out_8078866354536721695[7] = 1;
   out_8078866354536721695[8] = 0;
}
void h_27(double *state, double *unused, double *out_7579637098806142702) {
   out_7579637098806142702[0] = state[3];
}
void H_27(double *state, double *unused, double *out_7406921396118853036) {
   out_7406921396118853036[0] = 0;
   out_7406921396118853036[1] = 0;
   out_7406921396118853036[2] = 0;
   out_7406921396118853036[3] = 1;
   out_7406921396118853036[4] = 0;
   out_7406921396118853036[5] = 0;
   out_7406921396118853036[6] = 0;
   out_7406921396118853036[7] = 0;
   out_7406921396118853036[8] = 0;
}
void h_29(double *state, double *unused, double *out_8981601556956599670) {
   out_8981601556956599670[0] = state[1];
}
void H_29(double *state, double *unused, double *out_8354828021475881485) {
   out_8354828021475881485[0] = 0;
   out_8354828021475881485[1] = 1;
   out_8354828021475881485[2] = 0;
   out_8354828021475881485[3] = 0;
   out_8354828021475881485[4] = 0;
   out_8354828021475881485[5] = 0;
   out_8354828021475881485[6] = 0;
   out_8354828021475881485[7] = 0;
   out_8354828021475881485[8] = 0;
}
void h_28(double *state, double *unused, double *out_4659949187422787859) {
   out_4659949187422787859[0] = state[0];
}
void H_28(double *state, double *unused, double *out_5009517035164139557) {
   out_5009517035164139557[0] = 1;
   out_5009517035164139557[1] = 0;
   out_5009517035164139557[2] = 0;
   out_5009517035164139557[3] = 0;
   out_5009517035164139557[4] = 0;
   out_5009517035164139557[5] = 0;
   out_5009517035164139557[6] = 0;
   out_5009517035164139557[7] = 0;
   out_5009517035164139557[8] = 0;
}
void h_31(double *state, double *unused, double *out_7316065099871446436) {
   out_7316065099871446436[0] = state[8];
}
void H_31(double *state, double *unused, double *out_8705074456770073171) {
   out_8705074456770073171[0] = 0;
   out_8705074456770073171[1] = 0;
   out_8705074456770073171[2] = 0;
   out_8705074456770073171[3] = 0;
   out_8705074456770073171[4] = 0;
   out_8705074456770073171[5] = 0;
   out_8705074456770073171[6] = 0;
   out_8705074456770073171[7] = 0;
   out_8705074456770073171[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_2633561206191248032) {
  err_fun(nom_x, delta_x, out_2633561206191248032);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_5222322722539771080) {
  inv_err_fun(nom_x, true_x, out_5222322722539771080);
}
void car_H_mod_fun(double *state, double *out_4733519652188373948) {
  H_mod_fun(state, out_4733519652188373948);
}
void car_f_fun(double *state, double dt, double *out_9187320060872601910) {
  f_fun(state,  dt, out_9187320060872601910);
}
void car_F_fun(double *state, double dt, double *out_3219504763184105906) {
  F_fun(state,  dt, out_3219504763184105906);
}
void car_h_25(double *state, double *unused, double *out_1821652184812404746) {
  h_25(state, unused, out_1821652184812404746);
}
void car_H_25(double *state, double *unused, double *out_4337363035662665471) {
  H_25(state, unused, out_4337363035662665471);
}
void car_h_24(double *state, double *unused, double *out_258826568498121593) {
  h_24(state, unused, out_258826568498121593);
}
void car_H_24(double *state, double *unused, double *out_9206177900690372323) {
  H_24(state, unused, out_9206177900690372323);
}
void car_h_30(double *state, double *unused, double *out_1546458122527898857) {
  h_30(state, unused, out_1546458122527898857);
}
void car_H_30(double *state, double *unused, double *out_8865059365790273669) {
  H_30(state, unused, out_8865059365790273669);
}
void car_h_26(double *state, double *unused, double *out_4254367670776586025) {
  h_26(state, unused, out_4254367670776586025);
}
void car_H_26(double *state, double *unused, double *out_8078866354536721695) {
  H_26(state, unused, out_8078866354536721695);
}
void car_h_27(double *state, double *unused, double *out_7579637098806142702) {
  h_27(state, unused, out_7579637098806142702);
}
void car_H_27(double *state, double *unused, double *out_7406921396118853036) {
  H_27(state, unused, out_7406921396118853036);
}
void car_h_29(double *state, double *unused, double *out_8981601556956599670) {
  h_29(state, unused, out_8981601556956599670);
}
void car_H_29(double *state, double *unused, double *out_8354828021475881485) {
  H_29(state, unused, out_8354828021475881485);
}
void car_h_28(double *state, double *unused, double *out_4659949187422787859) {
  h_28(state, unused, out_4659949187422787859);
}
void car_H_28(double *state, double *unused, double *out_5009517035164139557) {
  H_28(state, unused, out_5009517035164139557);
}
void car_h_31(double *state, double *unused, double *out_7316065099871446436) {
  h_31(state, unused, out_7316065099871446436);
}
void car_H_31(double *state, double *unused, double *out_8705074456770073171) {
  H_31(state, unused, out_8705074456770073171);
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
