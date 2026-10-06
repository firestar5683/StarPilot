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
void err_fun(double *nom_x, double *delta_x, double *out_109358598230941622) {
   out_109358598230941622[0] = delta_x[0] + nom_x[0];
   out_109358598230941622[1] = delta_x[1] + nom_x[1];
   out_109358598230941622[2] = delta_x[2] + nom_x[2];
   out_109358598230941622[3] = delta_x[3] + nom_x[3];
   out_109358598230941622[4] = delta_x[4] + nom_x[4];
   out_109358598230941622[5] = delta_x[5] + nom_x[5];
   out_109358598230941622[6] = delta_x[6] + nom_x[6];
   out_109358598230941622[7] = delta_x[7] + nom_x[7];
   out_109358598230941622[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_4805958646442115899) {
   out_4805958646442115899[0] = -nom_x[0] + true_x[0];
   out_4805958646442115899[1] = -nom_x[1] + true_x[1];
   out_4805958646442115899[2] = -nom_x[2] + true_x[2];
   out_4805958646442115899[3] = -nom_x[3] + true_x[3];
   out_4805958646442115899[4] = -nom_x[4] + true_x[4];
   out_4805958646442115899[5] = -nom_x[5] + true_x[5];
   out_4805958646442115899[6] = -nom_x[6] + true_x[6];
   out_4805958646442115899[7] = -nom_x[7] + true_x[7];
   out_4805958646442115899[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_7514405629275931205) {
   out_7514405629275931205[0] = 1.0;
   out_7514405629275931205[1] = 0.0;
   out_7514405629275931205[2] = 0.0;
   out_7514405629275931205[3] = 0.0;
   out_7514405629275931205[4] = 0.0;
   out_7514405629275931205[5] = 0.0;
   out_7514405629275931205[6] = 0.0;
   out_7514405629275931205[7] = 0.0;
   out_7514405629275931205[8] = 0.0;
   out_7514405629275931205[9] = 0.0;
   out_7514405629275931205[10] = 1.0;
   out_7514405629275931205[11] = 0.0;
   out_7514405629275931205[12] = 0.0;
   out_7514405629275931205[13] = 0.0;
   out_7514405629275931205[14] = 0.0;
   out_7514405629275931205[15] = 0.0;
   out_7514405629275931205[16] = 0.0;
   out_7514405629275931205[17] = 0.0;
   out_7514405629275931205[18] = 0.0;
   out_7514405629275931205[19] = 0.0;
   out_7514405629275931205[20] = 1.0;
   out_7514405629275931205[21] = 0.0;
   out_7514405629275931205[22] = 0.0;
   out_7514405629275931205[23] = 0.0;
   out_7514405629275931205[24] = 0.0;
   out_7514405629275931205[25] = 0.0;
   out_7514405629275931205[26] = 0.0;
   out_7514405629275931205[27] = 0.0;
   out_7514405629275931205[28] = 0.0;
   out_7514405629275931205[29] = 0.0;
   out_7514405629275931205[30] = 1.0;
   out_7514405629275931205[31] = 0.0;
   out_7514405629275931205[32] = 0.0;
   out_7514405629275931205[33] = 0.0;
   out_7514405629275931205[34] = 0.0;
   out_7514405629275931205[35] = 0.0;
   out_7514405629275931205[36] = 0.0;
   out_7514405629275931205[37] = 0.0;
   out_7514405629275931205[38] = 0.0;
   out_7514405629275931205[39] = 0.0;
   out_7514405629275931205[40] = 1.0;
   out_7514405629275931205[41] = 0.0;
   out_7514405629275931205[42] = 0.0;
   out_7514405629275931205[43] = 0.0;
   out_7514405629275931205[44] = 0.0;
   out_7514405629275931205[45] = 0.0;
   out_7514405629275931205[46] = 0.0;
   out_7514405629275931205[47] = 0.0;
   out_7514405629275931205[48] = 0.0;
   out_7514405629275931205[49] = 0.0;
   out_7514405629275931205[50] = 1.0;
   out_7514405629275931205[51] = 0.0;
   out_7514405629275931205[52] = 0.0;
   out_7514405629275931205[53] = 0.0;
   out_7514405629275931205[54] = 0.0;
   out_7514405629275931205[55] = 0.0;
   out_7514405629275931205[56] = 0.0;
   out_7514405629275931205[57] = 0.0;
   out_7514405629275931205[58] = 0.0;
   out_7514405629275931205[59] = 0.0;
   out_7514405629275931205[60] = 1.0;
   out_7514405629275931205[61] = 0.0;
   out_7514405629275931205[62] = 0.0;
   out_7514405629275931205[63] = 0.0;
   out_7514405629275931205[64] = 0.0;
   out_7514405629275931205[65] = 0.0;
   out_7514405629275931205[66] = 0.0;
   out_7514405629275931205[67] = 0.0;
   out_7514405629275931205[68] = 0.0;
   out_7514405629275931205[69] = 0.0;
   out_7514405629275931205[70] = 1.0;
   out_7514405629275931205[71] = 0.0;
   out_7514405629275931205[72] = 0.0;
   out_7514405629275931205[73] = 0.0;
   out_7514405629275931205[74] = 0.0;
   out_7514405629275931205[75] = 0.0;
   out_7514405629275931205[76] = 0.0;
   out_7514405629275931205[77] = 0.0;
   out_7514405629275931205[78] = 0.0;
   out_7514405629275931205[79] = 0.0;
   out_7514405629275931205[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_673922476338472781) {
   out_673922476338472781[0] = state[0];
   out_673922476338472781[1] = state[1];
   out_673922476338472781[2] = state[2];
   out_673922476338472781[3] = state[3];
   out_673922476338472781[4] = state[4];
   out_673922476338472781[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_673922476338472781[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_673922476338472781[7] = state[7];
   out_673922476338472781[8] = state[8];
}
void F_fun(double *state, double dt, double *out_2470467678435225330) {
   out_2470467678435225330[0] = 1;
   out_2470467678435225330[1] = 0;
   out_2470467678435225330[2] = 0;
   out_2470467678435225330[3] = 0;
   out_2470467678435225330[4] = 0;
   out_2470467678435225330[5] = 0;
   out_2470467678435225330[6] = 0;
   out_2470467678435225330[7] = 0;
   out_2470467678435225330[8] = 0;
   out_2470467678435225330[9] = 0;
   out_2470467678435225330[10] = 1;
   out_2470467678435225330[11] = 0;
   out_2470467678435225330[12] = 0;
   out_2470467678435225330[13] = 0;
   out_2470467678435225330[14] = 0;
   out_2470467678435225330[15] = 0;
   out_2470467678435225330[16] = 0;
   out_2470467678435225330[17] = 0;
   out_2470467678435225330[18] = 0;
   out_2470467678435225330[19] = 0;
   out_2470467678435225330[20] = 1;
   out_2470467678435225330[21] = 0;
   out_2470467678435225330[22] = 0;
   out_2470467678435225330[23] = 0;
   out_2470467678435225330[24] = 0;
   out_2470467678435225330[25] = 0;
   out_2470467678435225330[26] = 0;
   out_2470467678435225330[27] = 0;
   out_2470467678435225330[28] = 0;
   out_2470467678435225330[29] = 0;
   out_2470467678435225330[30] = 1;
   out_2470467678435225330[31] = 0;
   out_2470467678435225330[32] = 0;
   out_2470467678435225330[33] = 0;
   out_2470467678435225330[34] = 0;
   out_2470467678435225330[35] = 0;
   out_2470467678435225330[36] = 0;
   out_2470467678435225330[37] = 0;
   out_2470467678435225330[38] = 0;
   out_2470467678435225330[39] = 0;
   out_2470467678435225330[40] = 1;
   out_2470467678435225330[41] = 0;
   out_2470467678435225330[42] = 0;
   out_2470467678435225330[43] = 0;
   out_2470467678435225330[44] = 0;
   out_2470467678435225330[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_2470467678435225330[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_2470467678435225330[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_2470467678435225330[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_2470467678435225330[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_2470467678435225330[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_2470467678435225330[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_2470467678435225330[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_2470467678435225330[53] = -9.8100000000000005*dt;
   out_2470467678435225330[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_2470467678435225330[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_2470467678435225330[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_2470467678435225330[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_2470467678435225330[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_2470467678435225330[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_2470467678435225330[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_2470467678435225330[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_2470467678435225330[62] = 0;
   out_2470467678435225330[63] = 0;
   out_2470467678435225330[64] = 0;
   out_2470467678435225330[65] = 0;
   out_2470467678435225330[66] = 0;
   out_2470467678435225330[67] = 0;
   out_2470467678435225330[68] = 0;
   out_2470467678435225330[69] = 0;
   out_2470467678435225330[70] = 1;
   out_2470467678435225330[71] = 0;
   out_2470467678435225330[72] = 0;
   out_2470467678435225330[73] = 0;
   out_2470467678435225330[74] = 0;
   out_2470467678435225330[75] = 0;
   out_2470467678435225330[76] = 0;
   out_2470467678435225330[77] = 0;
   out_2470467678435225330[78] = 0;
   out_2470467678435225330[79] = 0;
   out_2470467678435225330[80] = 1;
}
void h_25(double *state, double *unused, double *out_1981012656746252977) {
   out_1981012656746252977[0] = state[6];
}
void H_25(double *state, double *unused, double *out_3380974713598466874) {
   out_3380974713598466874[0] = 0;
   out_3380974713598466874[1] = 0;
   out_3380974713598466874[2] = 0;
   out_3380974713598466874[3] = 0;
   out_3380974713598466874[4] = 0;
   out_3380974713598466874[5] = 0;
   out_3380974713598466874[6] = 1;
   out_3380974713598466874[7] = 0;
   out_3380974713598466874[8] = 0;
}
void h_24(double *state, double *unused, double *out_6443218583231505463) {
   out_6443218583231505463[0] = state[4];
   out_6443218583231505463[1] = state[5];
}
void H_24(double *state, double *unused, double *out_3851432195641805598) {
   out_3851432195641805598[0] = 0;
   out_3851432195641805598[1] = 0;
   out_3851432195641805598[2] = 0;
   out_3851432195641805598[3] = 0;
   out_3851432195641805598[4] = 1;
   out_3851432195641805598[5] = 0;
   out_3851432195641805598[6] = 0;
   out_3851432195641805598[7] = 0;
   out_3851432195641805598[8] = 0;
   out_3851432195641805598[9] = 0;
   out_3851432195641805598[10] = 0;
   out_3851432195641805598[11] = 0;
   out_3851432195641805598[12] = 0;
   out_3851432195641805598[13] = 0;
   out_3851432195641805598[14] = 1;
   out_3851432195641805598[15] = 0;
   out_3851432195641805598[16] = 0;
   out_3851432195641805598[17] = 0;
}
void h_30(double *state, double *unused, double *out_1656436871507769373) {
   out_1656436871507769373[0] = state[4];
}
void H_30(double *state, double *unused, double *out_3510313660741706944) {
   out_3510313660741706944[0] = 0;
   out_3510313660741706944[1] = 0;
   out_3510313660741706944[2] = 0;
   out_3510313660741706944[3] = 0;
   out_3510313660741706944[4] = 1;
   out_3510313660741706944[5] = 0;
   out_3510313660741706944[6] = 0;
   out_3510313660741706944[7] = 0;
   out_3510313660741706944[8] = 0;
}
void h_26(double *state, double *unused, double *out_9091580305936470186) {
   out_9091580305936470186[0] = state[7];
}
void H_26(double *state, double *unused, double *out_2724120649488154970) {
   out_2724120649488154970[0] = 0;
   out_2724120649488154970[1] = 0;
   out_2724120649488154970[2] = 0;
   out_2724120649488154970[3] = 0;
   out_2724120649488154970[4] = 0;
   out_2724120649488154970[5] = 0;
   out_2724120649488154970[6] = 0;
   out_2724120649488154970[7] = 1;
   out_2724120649488154970[8] = 0;
}
void h_27(double *state, double *unused, double *out_3020660610914592668) {
   out_3020660610914592668[0] = state[3];
}
void H_27(double *state, double *unused, double *out_5685076972542131855) {
   out_5685076972542131855[0] = 0;
   out_5685076972542131855[1] = 0;
   out_5685076972542131855[2] = 0;
   out_5685076972542131855[3] = 1;
   out_5685076972542131855[4] = 0;
   out_5685076972542131855[5] = 0;
   out_5685076972542131855[6] = 0;
   out_5685076972542131855[7] = 0;
   out_5685076972542131855[8] = 0;
}
void h_29(double *state, double *unused, double *out_6658110139168615018) {
   out_6658110139168615018[0] = state[1];
}
void H_29(double *state, double *unused, double *out_3000082316427314760) {
   out_3000082316427314760[0] = 0;
   out_3000082316427314760[1] = 1;
   out_3000082316427314760[2] = 0;
   out_3000082316427314760[3] = 0;
   out_3000082316427314760[4] = 0;
   out_3000082316427314760[5] = 0;
   out_3000082316427314760[6] = 0;
   out_3000082316427314760[7] = 0;
   out_3000082316427314760[8] = 0;
}
void h_28(double *state, double *unused, double *out_5961308561092248097) {
   out_5961308561092248097[0] = state[0];
}
void H_28(double *state, double *unused, double *out_8082481333496845334) {
   out_8082481333496845334[0] = 1;
   out_8082481333496845334[1] = 0;
   out_8082481333496845334[2] = 0;
   out_8082481333496845334[3] = 0;
   out_8082481333496845334[4] = 0;
   out_8082481333496845334[5] = 0;
   out_8082481333496845334[6] = 0;
   out_8082481333496845334[7] = 0;
   out_8082481333496845334[8] = 0;
}
void h_31(double *state, double *unused, double *out_8568840583222548140) {
   out_8568840583222548140[0] = state[8];
}
void H_31(double *state, double *unused, double *out_3350328751721506446) {
   out_3350328751721506446[0] = 0;
   out_3350328751721506446[1] = 0;
   out_3350328751721506446[2] = 0;
   out_3350328751721506446[3] = 0;
   out_3350328751721506446[4] = 0;
   out_3350328751721506446[5] = 0;
   out_3350328751721506446[6] = 0;
   out_3350328751721506446[7] = 0;
   out_3350328751721506446[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_109358598230941622) {
  err_fun(nom_x, delta_x, out_109358598230941622);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_4805958646442115899) {
  inv_err_fun(nom_x, true_x, out_4805958646442115899);
}
void car_H_mod_fun(double *state, double *out_7514405629275931205) {
  H_mod_fun(state, out_7514405629275931205);
}
void car_f_fun(double *state, double dt, double *out_673922476338472781) {
  f_fun(state,  dt, out_673922476338472781);
}
void car_F_fun(double *state, double dt, double *out_2470467678435225330) {
  F_fun(state,  dt, out_2470467678435225330);
}
void car_h_25(double *state, double *unused, double *out_1981012656746252977) {
  h_25(state, unused, out_1981012656746252977);
}
void car_H_25(double *state, double *unused, double *out_3380974713598466874) {
  H_25(state, unused, out_3380974713598466874);
}
void car_h_24(double *state, double *unused, double *out_6443218583231505463) {
  h_24(state, unused, out_6443218583231505463);
}
void car_H_24(double *state, double *unused, double *out_3851432195641805598) {
  H_24(state, unused, out_3851432195641805598);
}
void car_h_30(double *state, double *unused, double *out_1656436871507769373) {
  h_30(state, unused, out_1656436871507769373);
}
void car_H_30(double *state, double *unused, double *out_3510313660741706944) {
  H_30(state, unused, out_3510313660741706944);
}
void car_h_26(double *state, double *unused, double *out_9091580305936470186) {
  h_26(state, unused, out_9091580305936470186);
}
void car_H_26(double *state, double *unused, double *out_2724120649488154970) {
  H_26(state, unused, out_2724120649488154970);
}
void car_h_27(double *state, double *unused, double *out_3020660610914592668) {
  h_27(state, unused, out_3020660610914592668);
}
void car_H_27(double *state, double *unused, double *out_5685076972542131855) {
  H_27(state, unused, out_5685076972542131855);
}
void car_h_29(double *state, double *unused, double *out_6658110139168615018) {
  h_29(state, unused, out_6658110139168615018);
}
void car_H_29(double *state, double *unused, double *out_3000082316427314760) {
  H_29(state, unused, out_3000082316427314760);
}
void car_h_28(double *state, double *unused, double *out_5961308561092248097) {
  h_28(state, unused, out_5961308561092248097);
}
void car_H_28(double *state, double *unused, double *out_8082481333496845334) {
  H_28(state, unused, out_8082481333496845334);
}
void car_h_31(double *state, double *unused, double *out_8568840583222548140) {
  h_31(state, unused, out_8568840583222548140);
}
void car_H_31(double *state, double *unused, double *out_3350328751721506446) {
  H_31(state, unused, out_3350328751721506446);
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
