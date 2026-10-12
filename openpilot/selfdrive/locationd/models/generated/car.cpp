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
void err_fun(double *nom_x, double *delta_x, double *out_4453381878183487431) {
   out_4453381878183487431[0] = delta_x[0] + nom_x[0];
   out_4453381878183487431[1] = delta_x[1] + nom_x[1];
   out_4453381878183487431[2] = delta_x[2] + nom_x[2];
   out_4453381878183487431[3] = delta_x[3] + nom_x[3];
   out_4453381878183487431[4] = delta_x[4] + nom_x[4];
   out_4453381878183487431[5] = delta_x[5] + nom_x[5];
   out_4453381878183487431[6] = delta_x[6] + nom_x[6];
   out_4453381878183487431[7] = delta_x[7] + nom_x[7];
   out_4453381878183487431[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_875318933667132564) {
   out_875318933667132564[0] = -nom_x[0] + true_x[0];
   out_875318933667132564[1] = -nom_x[1] + true_x[1];
   out_875318933667132564[2] = -nom_x[2] + true_x[2];
   out_875318933667132564[3] = -nom_x[3] + true_x[3];
   out_875318933667132564[4] = -nom_x[4] + true_x[4];
   out_875318933667132564[5] = -nom_x[5] + true_x[5];
   out_875318933667132564[6] = -nom_x[6] + true_x[6];
   out_875318933667132564[7] = -nom_x[7] + true_x[7];
   out_875318933667132564[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_8397482359330457307) {
   out_8397482359330457307[0] = 1.0;
   out_8397482359330457307[1] = 0.0;
   out_8397482359330457307[2] = 0.0;
   out_8397482359330457307[3] = 0.0;
   out_8397482359330457307[4] = 0.0;
   out_8397482359330457307[5] = 0.0;
   out_8397482359330457307[6] = 0.0;
   out_8397482359330457307[7] = 0.0;
   out_8397482359330457307[8] = 0.0;
   out_8397482359330457307[9] = 0.0;
   out_8397482359330457307[10] = 1.0;
   out_8397482359330457307[11] = 0.0;
   out_8397482359330457307[12] = 0.0;
   out_8397482359330457307[13] = 0.0;
   out_8397482359330457307[14] = 0.0;
   out_8397482359330457307[15] = 0.0;
   out_8397482359330457307[16] = 0.0;
   out_8397482359330457307[17] = 0.0;
   out_8397482359330457307[18] = 0.0;
   out_8397482359330457307[19] = 0.0;
   out_8397482359330457307[20] = 1.0;
   out_8397482359330457307[21] = 0.0;
   out_8397482359330457307[22] = 0.0;
   out_8397482359330457307[23] = 0.0;
   out_8397482359330457307[24] = 0.0;
   out_8397482359330457307[25] = 0.0;
   out_8397482359330457307[26] = 0.0;
   out_8397482359330457307[27] = 0.0;
   out_8397482359330457307[28] = 0.0;
   out_8397482359330457307[29] = 0.0;
   out_8397482359330457307[30] = 1.0;
   out_8397482359330457307[31] = 0.0;
   out_8397482359330457307[32] = 0.0;
   out_8397482359330457307[33] = 0.0;
   out_8397482359330457307[34] = 0.0;
   out_8397482359330457307[35] = 0.0;
   out_8397482359330457307[36] = 0.0;
   out_8397482359330457307[37] = 0.0;
   out_8397482359330457307[38] = 0.0;
   out_8397482359330457307[39] = 0.0;
   out_8397482359330457307[40] = 1.0;
   out_8397482359330457307[41] = 0.0;
   out_8397482359330457307[42] = 0.0;
   out_8397482359330457307[43] = 0.0;
   out_8397482359330457307[44] = 0.0;
   out_8397482359330457307[45] = 0.0;
   out_8397482359330457307[46] = 0.0;
   out_8397482359330457307[47] = 0.0;
   out_8397482359330457307[48] = 0.0;
   out_8397482359330457307[49] = 0.0;
   out_8397482359330457307[50] = 1.0;
   out_8397482359330457307[51] = 0.0;
   out_8397482359330457307[52] = 0.0;
   out_8397482359330457307[53] = 0.0;
   out_8397482359330457307[54] = 0.0;
   out_8397482359330457307[55] = 0.0;
   out_8397482359330457307[56] = 0.0;
   out_8397482359330457307[57] = 0.0;
   out_8397482359330457307[58] = 0.0;
   out_8397482359330457307[59] = 0.0;
   out_8397482359330457307[60] = 1.0;
   out_8397482359330457307[61] = 0.0;
   out_8397482359330457307[62] = 0.0;
   out_8397482359330457307[63] = 0.0;
   out_8397482359330457307[64] = 0.0;
   out_8397482359330457307[65] = 0.0;
   out_8397482359330457307[66] = 0.0;
   out_8397482359330457307[67] = 0.0;
   out_8397482359330457307[68] = 0.0;
   out_8397482359330457307[69] = 0.0;
   out_8397482359330457307[70] = 1.0;
   out_8397482359330457307[71] = 0.0;
   out_8397482359330457307[72] = 0.0;
   out_8397482359330457307[73] = 0.0;
   out_8397482359330457307[74] = 0.0;
   out_8397482359330457307[75] = 0.0;
   out_8397482359330457307[76] = 0.0;
   out_8397482359330457307[77] = 0.0;
   out_8397482359330457307[78] = 0.0;
   out_8397482359330457307[79] = 0.0;
   out_8397482359330457307[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_133753830955943846) {
   out_133753830955943846[0] = state[0];
   out_133753830955943846[1] = state[1];
   out_133753830955943846[2] = state[2];
   out_133753830955943846[3] = state[3];
   out_133753830955943846[4] = state[4];
   out_133753830955943846[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_133753830955943846[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_133753830955943846[7] = state[7];
   out_133753830955943846[8] = state[8];
}
void F_fun(double *state, double dt, double *out_7906645124566014609) {
   out_7906645124566014609[0] = 1;
   out_7906645124566014609[1] = 0;
   out_7906645124566014609[2] = 0;
   out_7906645124566014609[3] = 0;
   out_7906645124566014609[4] = 0;
   out_7906645124566014609[5] = 0;
   out_7906645124566014609[6] = 0;
   out_7906645124566014609[7] = 0;
   out_7906645124566014609[8] = 0;
   out_7906645124566014609[9] = 0;
   out_7906645124566014609[10] = 1;
   out_7906645124566014609[11] = 0;
   out_7906645124566014609[12] = 0;
   out_7906645124566014609[13] = 0;
   out_7906645124566014609[14] = 0;
   out_7906645124566014609[15] = 0;
   out_7906645124566014609[16] = 0;
   out_7906645124566014609[17] = 0;
   out_7906645124566014609[18] = 0;
   out_7906645124566014609[19] = 0;
   out_7906645124566014609[20] = 1;
   out_7906645124566014609[21] = 0;
   out_7906645124566014609[22] = 0;
   out_7906645124566014609[23] = 0;
   out_7906645124566014609[24] = 0;
   out_7906645124566014609[25] = 0;
   out_7906645124566014609[26] = 0;
   out_7906645124566014609[27] = 0;
   out_7906645124566014609[28] = 0;
   out_7906645124566014609[29] = 0;
   out_7906645124566014609[30] = 1;
   out_7906645124566014609[31] = 0;
   out_7906645124566014609[32] = 0;
   out_7906645124566014609[33] = 0;
   out_7906645124566014609[34] = 0;
   out_7906645124566014609[35] = 0;
   out_7906645124566014609[36] = 0;
   out_7906645124566014609[37] = 0;
   out_7906645124566014609[38] = 0;
   out_7906645124566014609[39] = 0;
   out_7906645124566014609[40] = 1;
   out_7906645124566014609[41] = 0;
   out_7906645124566014609[42] = 0;
   out_7906645124566014609[43] = 0;
   out_7906645124566014609[44] = 0;
   out_7906645124566014609[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_7906645124566014609[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_7906645124566014609[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_7906645124566014609[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_7906645124566014609[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_7906645124566014609[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_7906645124566014609[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_7906645124566014609[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_7906645124566014609[53] = -9.8100000000000005*dt;
   out_7906645124566014609[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_7906645124566014609[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_7906645124566014609[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_7906645124566014609[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_7906645124566014609[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_7906645124566014609[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_7906645124566014609[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_7906645124566014609[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_7906645124566014609[62] = 0;
   out_7906645124566014609[63] = 0;
   out_7906645124566014609[64] = 0;
   out_7906645124566014609[65] = 0;
   out_7906645124566014609[66] = 0;
   out_7906645124566014609[67] = 0;
   out_7906645124566014609[68] = 0;
   out_7906645124566014609[69] = 0;
   out_7906645124566014609[70] = 1;
   out_7906645124566014609[71] = 0;
   out_7906645124566014609[72] = 0;
   out_7906645124566014609[73] = 0;
   out_7906645124566014609[74] = 0;
   out_7906645124566014609[75] = 0;
   out_7906645124566014609[76] = 0;
   out_7906645124566014609[77] = 0;
   out_7906645124566014609[78] = 0;
   out_7906645124566014609[79] = 0;
   out_7906645124566014609[80] = 1;
}
void h_25(double *state, double *unused, double *out_1042419833926058116) {
   out_1042419833926058116[0] = state[6];
}
void H_25(double *state, double *unused, double *out_5254430871451225200) {
   out_5254430871451225200[0] = 0;
   out_5254430871451225200[1] = 0;
   out_5254430871451225200[2] = 0;
   out_5254430871451225200[3] = 0;
   out_5254430871451225200[4] = 0;
   out_5254430871451225200[5] = 0;
   out_5254430871451225200[6] = 1;
   out_5254430871451225200[7] = 0;
   out_5254430871451225200[8] = 0;
}
void h_24(double *state, double *unused, double *out_858315406556051163) {
   out_858315406556051163[0] = state[4];
   out_858315406556051163[1] = state[5];
}
void H_24(double *state, double *unused, double *out_5344959191384304354) {
   out_5344959191384304354[0] = 0;
   out_5344959191384304354[1] = 0;
   out_5344959191384304354[2] = 0;
   out_5344959191384304354[3] = 0;
   out_5344959191384304354[4] = 1;
   out_5344959191384304354[5] = 0;
   out_5344959191384304354[6] = 0;
   out_5344959191384304354[7] = 0;
   out_5344959191384304354[8] = 0;
   out_5344959191384304354[9] = 0;
   out_5344959191384304354[10] = 0;
   out_5344959191384304354[11] = 0;
   out_5344959191384304354[12] = 0;
   out_5344959191384304354[13] = 0;
   out_5344959191384304354[14] = 1;
   out_5344959191384304354[15] = 0;
   out_5344959191384304354[16] = 0;
   out_5344959191384304354[17] = 0;
}
void h_30(double *state, double *unused, double *out_6160796123059927854) {
   out_6160796123059927854[0] = state[4];
}
void H_30(double *state, double *unused, double *out_7772763829958473827) {
   out_7772763829958473827[0] = 0;
   out_7772763829958473827[1] = 0;
   out_7772763829958473827[2] = 0;
   out_7772763829958473827[3] = 0;
   out_7772763829958473827[4] = 1;
   out_7772763829958473827[5] = 0;
   out_7772763829958473827[6] = 0;
   out_7772763829958473827[7] = 0;
   out_7772763829958473827[8] = 0;
}
void h_26(double *state, double *unused, double *out_7284274682988778117) {
   out_7284274682988778117[0] = state[7];
}
void H_26(double *state, double *unused, double *out_1512927552577168976) {
   out_1512927552577168976[0] = 0;
   out_1512927552577168976[1] = 0;
   out_1512927552577168976[2] = 0;
   out_1512927552577168976[3] = 0;
   out_1512927552577168976[4] = 0;
   out_1512927552577168976[5] = 0;
   out_1512927552577168976[6] = 0;
   out_1512927552577168976[7] = 1;
   out_1512927552577168976[8] = 0;
}
void h_27(double *state, double *unused, double *out_557704697785718655) {
   out_557704697785718655[0] = state[3];
}
void H_27(double *state, double *unused, double *out_1448028770476807909) {
   out_1448028770476807909[0] = 0;
   out_1448028770476807909[1] = 0;
   out_1448028770476807909[2] = 0;
   out_1448028770476807909[3] = 1;
   out_1448028770476807909[4] = 0;
   out_1448028770476807909[5] = 0;
   out_1448028770476807909[6] = 0;
   out_1448028770476807909[7] = 0;
   out_1448028770476807909[8] = 0;
}
void h_29(double *state, double *unused, double *out_5886906433235774616) {
   out_5886906433235774616[0] = state[1];
}
void H_29(double *state, double *unused, double *out_1236965885638009186) {
   out_1236965885638009186[0] = 0;
   out_1236965885638009186[1] = 1;
   out_1236965885638009186[2] = 0;
   out_1236965885638009186[3] = 0;
   out_1236965885638009186[4] = 0;
   out_1236965885638009186[5] = 0;
   out_1236965885638009186[6] = 0;
   out_1236965885638009186[7] = 0;
   out_1236965885638009186[8] = 0;
}
void h_28(double *state, double *unused, double *out_7336233453404305132) {
   out_7336233453404305132[0] = state[0];
}
void H_28(double *state, double *unused, double *out_3200596157203335437) {
   out_3200596157203335437[0] = 1;
   out_3200596157203335437[1] = 0;
   out_3200596157203335437[2] = 0;
   out_3200596157203335437[3] = 0;
   out_3200596157203335437[4] = 0;
   out_3200596157203335437[5] = 0;
   out_3200596157203335437[6] = 0;
   out_3200596157203335437[7] = 0;
   out_3200596157203335437[8] = 0;
}
void h_31(double *state, double *unused, double *out_767225771641552227) {
   out_767225771641552227[0] = state[8];
}
void H_31(double *state, double *unused, double *out_886719450343817500) {
   out_886719450343817500[0] = 0;
   out_886719450343817500[1] = 0;
   out_886719450343817500[2] = 0;
   out_886719450343817500[3] = 0;
   out_886719450343817500[4] = 0;
   out_886719450343817500[5] = 0;
   out_886719450343817500[6] = 0;
   out_886719450343817500[7] = 0;
   out_886719450343817500[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_4453381878183487431) {
  err_fun(nom_x, delta_x, out_4453381878183487431);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_875318933667132564) {
  inv_err_fun(nom_x, true_x, out_875318933667132564);
}
void car_H_mod_fun(double *state, double *out_8397482359330457307) {
  H_mod_fun(state, out_8397482359330457307);
}
void car_f_fun(double *state, double dt, double *out_133753830955943846) {
  f_fun(state,  dt, out_133753830955943846);
}
void car_F_fun(double *state, double dt, double *out_7906645124566014609) {
  F_fun(state,  dt, out_7906645124566014609);
}
void car_h_25(double *state, double *unused, double *out_1042419833926058116) {
  h_25(state, unused, out_1042419833926058116);
}
void car_H_25(double *state, double *unused, double *out_5254430871451225200) {
  H_25(state, unused, out_5254430871451225200);
}
void car_h_24(double *state, double *unused, double *out_858315406556051163) {
  h_24(state, unused, out_858315406556051163);
}
void car_H_24(double *state, double *unused, double *out_5344959191384304354) {
  H_24(state, unused, out_5344959191384304354);
}
void car_h_30(double *state, double *unused, double *out_6160796123059927854) {
  h_30(state, unused, out_6160796123059927854);
}
void car_H_30(double *state, double *unused, double *out_7772763829958473827) {
  H_30(state, unused, out_7772763829958473827);
}
void car_h_26(double *state, double *unused, double *out_7284274682988778117) {
  h_26(state, unused, out_7284274682988778117);
}
void car_H_26(double *state, double *unused, double *out_1512927552577168976) {
  H_26(state, unused, out_1512927552577168976);
}
void car_h_27(double *state, double *unused, double *out_557704697785718655) {
  h_27(state, unused, out_557704697785718655);
}
void car_H_27(double *state, double *unused, double *out_1448028770476807909) {
  H_27(state, unused, out_1448028770476807909);
}
void car_h_29(double *state, double *unused, double *out_5886906433235774616) {
  h_29(state, unused, out_5886906433235774616);
}
void car_H_29(double *state, double *unused, double *out_1236965885638009186) {
  H_29(state, unused, out_1236965885638009186);
}
void car_h_28(double *state, double *unused, double *out_7336233453404305132) {
  h_28(state, unused, out_7336233453404305132);
}
void car_H_28(double *state, double *unused, double *out_3200596157203335437) {
  H_28(state, unused, out_3200596157203335437);
}
void car_h_31(double *state, double *unused, double *out_767225771641552227) {
  h_31(state, unused, out_767225771641552227);
}
void car_H_31(double *state, double *unused, double *out_886719450343817500) {
  H_31(state, unused, out_886719450343817500);
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
