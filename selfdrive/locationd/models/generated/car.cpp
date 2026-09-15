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
void err_fun(double *nom_x, double *delta_x, double *out_6543135761510689107) {
   out_6543135761510689107[0] = delta_x[0] + nom_x[0];
   out_6543135761510689107[1] = delta_x[1] + nom_x[1];
   out_6543135761510689107[2] = delta_x[2] + nom_x[2];
   out_6543135761510689107[3] = delta_x[3] + nom_x[3];
   out_6543135761510689107[4] = delta_x[4] + nom_x[4];
   out_6543135761510689107[5] = delta_x[5] + nom_x[5];
   out_6543135761510689107[6] = delta_x[6] + nom_x[6];
   out_6543135761510689107[7] = delta_x[7] + nom_x[7];
   out_6543135761510689107[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_2331655545426529005) {
   out_2331655545426529005[0] = -nom_x[0] + true_x[0];
   out_2331655545426529005[1] = -nom_x[1] + true_x[1];
   out_2331655545426529005[2] = -nom_x[2] + true_x[2];
   out_2331655545426529005[3] = -nom_x[3] + true_x[3];
   out_2331655545426529005[4] = -nom_x[4] + true_x[4];
   out_2331655545426529005[5] = -nom_x[5] + true_x[5];
   out_2331655545426529005[6] = -nom_x[6] + true_x[6];
   out_2331655545426529005[7] = -nom_x[7] + true_x[7];
   out_2331655545426529005[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_6389313126975023722) {
   out_6389313126975023722[0] = 1.0;
   out_6389313126975023722[1] = 0.0;
   out_6389313126975023722[2] = 0.0;
   out_6389313126975023722[3] = 0.0;
   out_6389313126975023722[4] = 0.0;
   out_6389313126975023722[5] = 0.0;
   out_6389313126975023722[6] = 0.0;
   out_6389313126975023722[7] = 0.0;
   out_6389313126975023722[8] = 0.0;
   out_6389313126975023722[9] = 0.0;
   out_6389313126975023722[10] = 1.0;
   out_6389313126975023722[11] = 0.0;
   out_6389313126975023722[12] = 0.0;
   out_6389313126975023722[13] = 0.0;
   out_6389313126975023722[14] = 0.0;
   out_6389313126975023722[15] = 0.0;
   out_6389313126975023722[16] = 0.0;
   out_6389313126975023722[17] = 0.0;
   out_6389313126975023722[18] = 0.0;
   out_6389313126975023722[19] = 0.0;
   out_6389313126975023722[20] = 1.0;
   out_6389313126975023722[21] = 0.0;
   out_6389313126975023722[22] = 0.0;
   out_6389313126975023722[23] = 0.0;
   out_6389313126975023722[24] = 0.0;
   out_6389313126975023722[25] = 0.0;
   out_6389313126975023722[26] = 0.0;
   out_6389313126975023722[27] = 0.0;
   out_6389313126975023722[28] = 0.0;
   out_6389313126975023722[29] = 0.0;
   out_6389313126975023722[30] = 1.0;
   out_6389313126975023722[31] = 0.0;
   out_6389313126975023722[32] = 0.0;
   out_6389313126975023722[33] = 0.0;
   out_6389313126975023722[34] = 0.0;
   out_6389313126975023722[35] = 0.0;
   out_6389313126975023722[36] = 0.0;
   out_6389313126975023722[37] = 0.0;
   out_6389313126975023722[38] = 0.0;
   out_6389313126975023722[39] = 0.0;
   out_6389313126975023722[40] = 1.0;
   out_6389313126975023722[41] = 0.0;
   out_6389313126975023722[42] = 0.0;
   out_6389313126975023722[43] = 0.0;
   out_6389313126975023722[44] = 0.0;
   out_6389313126975023722[45] = 0.0;
   out_6389313126975023722[46] = 0.0;
   out_6389313126975023722[47] = 0.0;
   out_6389313126975023722[48] = 0.0;
   out_6389313126975023722[49] = 0.0;
   out_6389313126975023722[50] = 1.0;
   out_6389313126975023722[51] = 0.0;
   out_6389313126975023722[52] = 0.0;
   out_6389313126975023722[53] = 0.0;
   out_6389313126975023722[54] = 0.0;
   out_6389313126975023722[55] = 0.0;
   out_6389313126975023722[56] = 0.0;
   out_6389313126975023722[57] = 0.0;
   out_6389313126975023722[58] = 0.0;
   out_6389313126975023722[59] = 0.0;
   out_6389313126975023722[60] = 1.0;
   out_6389313126975023722[61] = 0.0;
   out_6389313126975023722[62] = 0.0;
   out_6389313126975023722[63] = 0.0;
   out_6389313126975023722[64] = 0.0;
   out_6389313126975023722[65] = 0.0;
   out_6389313126975023722[66] = 0.0;
   out_6389313126975023722[67] = 0.0;
   out_6389313126975023722[68] = 0.0;
   out_6389313126975023722[69] = 0.0;
   out_6389313126975023722[70] = 1.0;
   out_6389313126975023722[71] = 0.0;
   out_6389313126975023722[72] = 0.0;
   out_6389313126975023722[73] = 0.0;
   out_6389313126975023722[74] = 0.0;
   out_6389313126975023722[75] = 0.0;
   out_6389313126975023722[76] = 0.0;
   out_6389313126975023722[77] = 0.0;
   out_6389313126975023722[78] = 0.0;
   out_6389313126975023722[79] = 0.0;
   out_6389313126975023722[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_4897785971793930733) {
   out_4897785971793930733[0] = state[0];
   out_4897785971793930733[1] = state[1];
   out_4897785971793930733[2] = state[2];
   out_4897785971793930733[3] = state[3];
   out_4897785971793930733[4] = state[4];
   out_4897785971793930733[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_4897785971793930733[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_4897785971793930733[7] = state[7];
   out_4897785971793930733[8] = state[8];
}
void F_fun(double *state, double dt, double *out_1120359963151235251) {
   out_1120359963151235251[0] = 1;
   out_1120359963151235251[1] = 0;
   out_1120359963151235251[2] = 0;
   out_1120359963151235251[3] = 0;
   out_1120359963151235251[4] = 0;
   out_1120359963151235251[5] = 0;
   out_1120359963151235251[6] = 0;
   out_1120359963151235251[7] = 0;
   out_1120359963151235251[8] = 0;
   out_1120359963151235251[9] = 0;
   out_1120359963151235251[10] = 1;
   out_1120359963151235251[11] = 0;
   out_1120359963151235251[12] = 0;
   out_1120359963151235251[13] = 0;
   out_1120359963151235251[14] = 0;
   out_1120359963151235251[15] = 0;
   out_1120359963151235251[16] = 0;
   out_1120359963151235251[17] = 0;
   out_1120359963151235251[18] = 0;
   out_1120359963151235251[19] = 0;
   out_1120359963151235251[20] = 1;
   out_1120359963151235251[21] = 0;
   out_1120359963151235251[22] = 0;
   out_1120359963151235251[23] = 0;
   out_1120359963151235251[24] = 0;
   out_1120359963151235251[25] = 0;
   out_1120359963151235251[26] = 0;
   out_1120359963151235251[27] = 0;
   out_1120359963151235251[28] = 0;
   out_1120359963151235251[29] = 0;
   out_1120359963151235251[30] = 1;
   out_1120359963151235251[31] = 0;
   out_1120359963151235251[32] = 0;
   out_1120359963151235251[33] = 0;
   out_1120359963151235251[34] = 0;
   out_1120359963151235251[35] = 0;
   out_1120359963151235251[36] = 0;
   out_1120359963151235251[37] = 0;
   out_1120359963151235251[38] = 0;
   out_1120359963151235251[39] = 0;
   out_1120359963151235251[40] = 1;
   out_1120359963151235251[41] = 0;
   out_1120359963151235251[42] = 0;
   out_1120359963151235251[43] = 0;
   out_1120359963151235251[44] = 0;
   out_1120359963151235251[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_1120359963151235251[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_1120359963151235251[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_1120359963151235251[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_1120359963151235251[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_1120359963151235251[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_1120359963151235251[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_1120359963151235251[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_1120359963151235251[53] = -9.8100000000000005*dt;
   out_1120359963151235251[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_1120359963151235251[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_1120359963151235251[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_1120359963151235251[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_1120359963151235251[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_1120359963151235251[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_1120359963151235251[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_1120359963151235251[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_1120359963151235251[62] = 0;
   out_1120359963151235251[63] = 0;
   out_1120359963151235251[64] = 0;
   out_1120359963151235251[65] = 0;
   out_1120359963151235251[66] = 0;
   out_1120359963151235251[67] = 0;
   out_1120359963151235251[68] = 0;
   out_1120359963151235251[69] = 0;
   out_1120359963151235251[70] = 1;
   out_1120359963151235251[71] = 0;
   out_1120359963151235251[72] = 0;
   out_1120359963151235251[73] = 0;
   out_1120359963151235251[74] = 0;
   out_1120359963151235251[75] = 0;
   out_1120359963151235251[76] = 0;
   out_1120359963151235251[77] = 0;
   out_1120359963151235251[78] = 0;
   out_1120359963151235251[79] = 0;
   out_1120359963151235251[80] = 1;
}
void h_25(double *state, double *unused, double *out_2169501381777287353) {
   out_2169501381777287353[0] = state[6];
}
void H_25(double *state, double *unused, double *out_1485621301790358882) {
   out_1485621301790358882[0] = 0;
   out_1485621301790358882[1] = 0;
   out_1485621301790358882[2] = 0;
   out_1485621301790358882[3] = 0;
   out_1485621301790358882[4] = 0;
   out_1485621301790358882[5] = 0;
   out_1485621301790358882[6] = 1;
   out_1485621301790358882[7] = 0;
   out_1485621301790358882[8] = 0;
}
void h_24(double *state, double *unused, double *out_8386299954951130399) {
   out_8386299954951130399[0] = state[4];
   out_8386299954951130399[1] = state[5];
}
void H_24(double *state, double *unused, double *out_1956078783833697606) {
   out_1956078783833697606[0] = 0;
   out_1956078783833697606[1] = 0;
   out_1956078783833697606[2] = 0;
   out_1956078783833697606[3] = 0;
   out_1956078783833697606[4] = 1;
   out_1956078783833697606[5] = 0;
   out_1956078783833697606[6] = 0;
   out_1956078783833697606[7] = 0;
   out_1956078783833697606[8] = 0;
   out_1956078783833697606[9] = 0;
   out_1956078783833697606[10] = 0;
   out_1956078783833697606[11] = 0;
   out_1956078783833697606[12] = 0;
   out_1956078783833697606[13] = 0;
   out_1956078783833697606[14] = 1;
   out_1956078783833697606[15] = 0;
   out_1956078783833697606[16] = 0;
   out_1956078783833697606[17] = 0;
}
void h_30(double *state, double *unused, double *out_2444695444061793242) {
   out_2444695444061793242[0] = state[4];
}
void H_30(double *state, double *unused, double *out_6013317631917967080) {
   out_6013317631917967080[0] = 0;
   out_6013317631917967080[1] = 0;
   out_6013317631917967080[2] = 0;
   out_6013317631917967080[3] = 0;
   out_6013317631917967080[4] = 1;
   out_6013317631917967080[5] = 0;
   out_6013317631917967080[6] = 0;
   out_6013317631917967080[7] = 0;
   out_6013317631917967080[8] = 0;
}
void h_26(double *state, double *unused, double *out_2413046201872073325) {
   out_2413046201872073325[0] = state[7];
}
void H_26(double *state, double *unused, double *out_5227124620664415106) {
   out_5227124620664415106[0] = 0;
   out_5227124620664415106[1] = 0;
   out_5227124620664415106[2] = 0;
   out_5227124620664415106[3] = 0;
   out_5227124620664415106[4] = 0;
   out_5227124620664415106[5] = 0;
   out_5227124620664415106[6] = 0;
   out_5227124620664415106[7] = 1;
   out_5227124620664415106[8] = 0;
}
void h_27(double *state, double *unused, double *out_6236155437866939300) {
   out_6236155437866939300[0] = state[3];
}
void H_27(double *state, double *unused, double *out_3789723560734023863) {
   out_3789723560734023863[0] = 0;
   out_3789723560734023863[1] = 0;
   out_3789723560734023863[2] = 0;
   out_3789723560734023863[3] = 1;
   out_3789723560734023863[4] = 0;
   out_3789723560734023863[5] = 0;
   out_3789723560734023863[6] = 0;
   out_3789723560734023863[7] = 0;
   out_3789723560734023863[8] = 0;
}
void h_29(double *state, double *unused, double *out_1645117212887109885) {
   out_1645117212887109885[0] = state[1];
}
void H_29(double *state, double *unused, double *out_5503086287603574896) {
   out_5503086287603574896[0] = 0;
   out_5503086287603574896[1] = 1;
   out_5503086287603574896[2] = 0;
   out_5503086287603574896[3] = 0;
   out_5503086287603574896[4] = 0;
   out_5503086287603574896[5] = 0;
   out_5503086287603574896[6] = 0;
   out_5503086287603574896[7] = 0;
   out_5503086287603574896[8] = 0;
}
void h_28(double *state, double *unused, double *out_5811547118428763170) {
   out_5811547118428763170[0] = state[0];
}
void H_28(double *state, double *unused, double *out_3539456016038248645) {
   out_3539456016038248645[0] = 1;
   out_3539456016038248645[1] = 0;
   out_3539456016038248645[2] = 0;
   out_3539456016038248645[3] = 0;
   out_3539456016038248645[4] = 0;
   out_3539456016038248645[5] = 0;
   out_3539456016038248645[6] = 0;
   out_3539456016038248645[7] = 0;
   out_3539456016038248645[8] = 0;
}
void h_31(double *state, double *unused, double *out_2741168024264044953) {
   out_2741168024264044953[0] = state[8];
}
void H_31(double *state, double *unused, double *out_1454975339913398454) {
   out_1454975339913398454[0] = 0;
   out_1454975339913398454[1] = 0;
   out_1454975339913398454[2] = 0;
   out_1454975339913398454[3] = 0;
   out_1454975339913398454[4] = 0;
   out_1454975339913398454[5] = 0;
   out_1454975339913398454[6] = 0;
   out_1454975339913398454[7] = 0;
   out_1454975339913398454[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_6543135761510689107) {
  err_fun(nom_x, delta_x, out_6543135761510689107);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_2331655545426529005) {
  inv_err_fun(nom_x, true_x, out_2331655545426529005);
}
void car_H_mod_fun(double *state, double *out_6389313126975023722) {
  H_mod_fun(state, out_6389313126975023722);
}
void car_f_fun(double *state, double dt, double *out_4897785971793930733) {
  f_fun(state,  dt, out_4897785971793930733);
}
void car_F_fun(double *state, double dt, double *out_1120359963151235251) {
  F_fun(state,  dt, out_1120359963151235251);
}
void car_h_25(double *state, double *unused, double *out_2169501381777287353) {
  h_25(state, unused, out_2169501381777287353);
}
void car_H_25(double *state, double *unused, double *out_1485621301790358882) {
  H_25(state, unused, out_1485621301790358882);
}
void car_h_24(double *state, double *unused, double *out_8386299954951130399) {
  h_24(state, unused, out_8386299954951130399);
}
void car_H_24(double *state, double *unused, double *out_1956078783833697606) {
  H_24(state, unused, out_1956078783833697606);
}
void car_h_30(double *state, double *unused, double *out_2444695444061793242) {
  h_30(state, unused, out_2444695444061793242);
}
void car_H_30(double *state, double *unused, double *out_6013317631917967080) {
  H_30(state, unused, out_6013317631917967080);
}
void car_h_26(double *state, double *unused, double *out_2413046201872073325) {
  h_26(state, unused, out_2413046201872073325);
}
void car_H_26(double *state, double *unused, double *out_5227124620664415106) {
  H_26(state, unused, out_5227124620664415106);
}
void car_h_27(double *state, double *unused, double *out_6236155437866939300) {
  h_27(state, unused, out_6236155437866939300);
}
void car_H_27(double *state, double *unused, double *out_3789723560734023863) {
  H_27(state, unused, out_3789723560734023863);
}
void car_h_29(double *state, double *unused, double *out_1645117212887109885) {
  h_29(state, unused, out_1645117212887109885);
}
void car_H_29(double *state, double *unused, double *out_5503086287603574896) {
  H_29(state, unused, out_5503086287603574896);
}
void car_h_28(double *state, double *unused, double *out_5811547118428763170) {
  h_28(state, unused, out_5811547118428763170);
}
void car_H_28(double *state, double *unused, double *out_3539456016038248645) {
  H_28(state, unused, out_3539456016038248645);
}
void car_h_31(double *state, double *unused, double *out_2741168024264044953) {
  h_31(state, unused, out_2741168024264044953);
}
void car_H_31(double *state, double *unused, double *out_1454975339913398454) {
  H_31(state, unused, out_1454975339913398454);
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
