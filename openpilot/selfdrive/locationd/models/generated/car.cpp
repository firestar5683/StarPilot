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
void err_fun(double *nom_x, double *delta_x, double *out_2769656543589876252) {
   out_2769656543589876252[0] = delta_x[0] + nom_x[0];
   out_2769656543589876252[1] = delta_x[1] + nom_x[1];
   out_2769656543589876252[2] = delta_x[2] + nom_x[2];
   out_2769656543589876252[3] = delta_x[3] + nom_x[3];
   out_2769656543589876252[4] = delta_x[4] + nom_x[4];
   out_2769656543589876252[5] = delta_x[5] + nom_x[5];
   out_2769656543589876252[6] = delta_x[6] + nom_x[6];
   out_2769656543589876252[7] = delta_x[7] + nom_x[7];
   out_2769656543589876252[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_6259280918951514600) {
   out_6259280918951514600[0] = -nom_x[0] + true_x[0];
   out_6259280918951514600[1] = -nom_x[1] + true_x[1];
   out_6259280918951514600[2] = -nom_x[2] + true_x[2];
   out_6259280918951514600[3] = -nom_x[3] + true_x[3];
   out_6259280918951514600[4] = -nom_x[4] + true_x[4];
   out_6259280918951514600[5] = -nom_x[5] + true_x[5];
   out_6259280918951514600[6] = -nom_x[6] + true_x[6];
   out_6259280918951514600[7] = -nom_x[7] + true_x[7];
   out_6259280918951514600[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_6437777562673898302) {
   out_6437777562673898302[0] = 1.0;
   out_6437777562673898302[1] = 0.0;
   out_6437777562673898302[2] = 0.0;
   out_6437777562673898302[3] = 0.0;
   out_6437777562673898302[4] = 0.0;
   out_6437777562673898302[5] = 0.0;
   out_6437777562673898302[6] = 0.0;
   out_6437777562673898302[7] = 0.0;
   out_6437777562673898302[8] = 0.0;
   out_6437777562673898302[9] = 0.0;
   out_6437777562673898302[10] = 1.0;
   out_6437777562673898302[11] = 0.0;
   out_6437777562673898302[12] = 0.0;
   out_6437777562673898302[13] = 0.0;
   out_6437777562673898302[14] = 0.0;
   out_6437777562673898302[15] = 0.0;
   out_6437777562673898302[16] = 0.0;
   out_6437777562673898302[17] = 0.0;
   out_6437777562673898302[18] = 0.0;
   out_6437777562673898302[19] = 0.0;
   out_6437777562673898302[20] = 1.0;
   out_6437777562673898302[21] = 0.0;
   out_6437777562673898302[22] = 0.0;
   out_6437777562673898302[23] = 0.0;
   out_6437777562673898302[24] = 0.0;
   out_6437777562673898302[25] = 0.0;
   out_6437777562673898302[26] = 0.0;
   out_6437777562673898302[27] = 0.0;
   out_6437777562673898302[28] = 0.0;
   out_6437777562673898302[29] = 0.0;
   out_6437777562673898302[30] = 1.0;
   out_6437777562673898302[31] = 0.0;
   out_6437777562673898302[32] = 0.0;
   out_6437777562673898302[33] = 0.0;
   out_6437777562673898302[34] = 0.0;
   out_6437777562673898302[35] = 0.0;
   out_6437777562673898302[36] = 0.0;
   out_6437777562673898302[37] = 0.0;
   out_6437777562673898302[38] = 0.0;
   out_6437777562673898302[39] = 0.0;
   out_6437777562673898302[40] = 1.0;
   out_6437777562673898302[41] = 0.0;
   out_6437777562673898302[42] = 0.0;
   out_6437777562673898302[43] = 0.0;
   out_6437777562673898302[44] = 0.0;
   out_6437777562673898302[45] = 0.0;
   out_6437777562673898302[46] = 0.0;
   out_6437777562673898302[47] = 0.0;
   out_6437777562673898302[48] = 0.0;
   out_6437777562673898302[49] = 0.0;
   out_6437777562673898302[50] = 1.0;
   out_6437777562673898302[51] = 0.0;
   out_6437777562673898302[52] = 0.0;
   out_6437777562673898302[53] = 0.0;
   out_6437777562673898302[54] = 0.0;
   out_6437777562673898302[55] = 0.0;
   out_6437777562673898302[56] = 0.0;
   out_6437777562673898302[57] = 0.0;
   out_6437777562673898302[58] = 0.0;
   out_6437777562673898302[59] = 0.0;
   out_6437777562673898302[60] = 1.0;
   out_6437777562673898302[61] = 0.0;
   out_6437777562673898302[62] = 0.0;
   out_6437777562673898302[63] = 0.0;
   out_6437777562673898302[64] = 0.0;
   out_6437777562673898302[65] = 0.0;
   out_6437777562673898302[66] = 0.0;
   out_6437777562673898302[67] = 0.0;
   out_6437777562673898302[68] = 0.0;
   out_6437777562673898302[69] = 0.0;
   out_6437777562673898302[70] = 1.0;
   out_6437777562673898302[71] = 0.0;
   out_6437777562673898302[72] = 0.0;
   out_6437777562673898302[73] = 0.0;
   out_6437777562673898302[74] = 0.0;
   out_6437777562673898302[75] = 0.0;
   out_6437777562673898302[76] = 0.0;
   out_6437777562673898302[77] = 0.0;
   out_6437777562673898302[78] = 0.0;
   out_6437777562673898302[79] = 0.0;
   out_6437777562673898302[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_1051826260233084185) {
   out_1051826260233084185[0] = state[0];
   out_1051826260233084185[1] = state[1];
   out_1051826260233084185[2] = state[2];
   out_1051826260233084185[3] = state[3];
   out_1051826260233084185[4] = state[4];
   out_1051826260233084185[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_1051826260233084185[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_1051826260233084185[7] = state[7];
   out_1051826260233084185[8] = state[8];
}
void F_fun(double *state, double dt, double *out_4665134552691392129) {
   out_4665134552691392129[0] = 1;
   out_4665134552691392129[1] = 0;
   out_4665134552691392129[2] = 0;
   out_4665134552691392129[3] = 0;
   out_4665134552691392129[4] = 0;
   out_4665134552691392129[5] = 0;
   out_4665134552691392129[6] = 0;
   out_4665134552691392129[7] = 0;
   out_4665134552691392129[8] = 0;
   out_4665134552691392129[9] = 0;
   out_4665134552691392129[10] = 1;
   out_4665134552691392129[11] = 0;
   out_4665134552691392129[12] = 0;
   out_4665134552691392129[13] = 0;
   out_4665134552691392129[14] = 0;
   out_4665134552691392129[15] = 0;
   out_4665134552691392129[16] = 0;
   out_4665134552691392129[17] = 0;
   out_4665134552691392129[18] = 0;
   out_4665134552691392129[19] = 0;
   out_4665134552691392129[20] = 1;
   out_4665134552691392129[21] = 0;
   out_4665134552691392129[22] = 0;
   out_4665134552691392129[23] = 0;
   out_4665134552691392129[24] = 0;
   out_4665134552691392129[25] = 0;
   out_4665134552691392129[26] = 0;
   out_4665134552691392129[27] = 0;
   out_4665134552691392129[28] = 0;
   out_4665134552691392129[29] = 0;
   out_4665134552691392129[30] = 1;
   out_4665134552691392129[31] = 0;
   out_4665134552691392129[32] = 0;
   out_4665134552691392129[33] = 0;
   out_4665134552691392129[34] = 0;
   out_4665134552691392129[35] = 0;
   out_4665134552691392129[36] = 0;
   out_4665134552691392129[37] = 0;
   out_4665134552691392129[38] = 0;
   out_4665134552691392129[39] = 0;
   out_4665134552691392129[40] = 1;
   out_4665134552691392129[41] = 0;
   out_4665134552691392129[42] = 0;
   out_4665134552691392129[43] = 0;
   out_4665134552691392129[44] = 0;
   out_4665134552691392129[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_4665134552691392129[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_4665134552691392129[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_4665134552691392129[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_4665134552691392129[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_4665134552691392129[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_4665134552691392129[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_4665134552691392129[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_4665134552691392129[53] = -9.8100000000000005*dt;
   out_4665134552691392129[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_4665134552691392129[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_4665134552691392129[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_4665134552691392129[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_4665134552691392129[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_4665134552691392129[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_4665134552691392129[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_4665134552691392129[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_4665134552691392129[62] = 0;
   out_4665134552691392129[63] = 0;
   out_4665134552691392129[64] = 0;
   out_4665134552691392129[65] = 0;
   out_4665134552691392129[66] = 0;
   out_4665134552691392129[67] = 0;
   out_4665134552691392129[68] = 0;
   out_4665134552691392129[69] = 0;
   out_4665134552691392129[70] = 1;
   out_4665134552691392129[71] = 0;
   out_4665134552691392129[72] = 0;
   out_4665134552691392129[73] = 0;
   out_4665134552691392129[74] = 0;
   out_4665134552691392129[75] = 0;
   out_4665134552691392129[76] = 0;
   out_4665134552691392129[77] = 0;
   out_4665134552691392129[78] = 0;
   out_4665134552691392129[79] = 0;
   out_4665134552691392129[80] = 1;
}
void h_25(double *state, double *unused, double *out_6902882259189952535) {
   out_6902882259189952535[0] = state[6];
}
void H_25(double *state, double *unused, double *out_2815778285123416077) {
   out_2815778285123416077[0] = 0;
   out_2815778285123416077[1] = 0;
   out_2815778285123416077[2] = 0;
   out_2815778285123416077[3] = 0;
   out_2815778285123416077[4] = 0;
   out_2815778285123416077[5] = 0;
   out_2815778285123416077[6] = 1;
   out_2815778285123416077[7] = 0;
   out_2815778285123416077[8] = 0;
}
void h_24(double *state, double *unused, double *out_4770294784793454035) {
   out_4770294784793454035[0] = state[4];
   out_4770294784793454035[1] = state[5];
}
void H_24(double *state, double *unused, double *out_5041486069102284639) {
   out_5041486069102284639[0] = 0;
   out_5041486069102284639[1] = 0;
   out_5041486069102284639[2] = 0;
   out_5041486069102284639[3] = 0;
   out_5041486069102284639[4] = 1;
   out_5041486069102284639[5] = 0;
   out_5041486069102284639[6] = 0;
   out_5041486069102284639[7] = 0;
   out_5041486069102284639[8] = 0;
   out_5041486069102284639[9] = 0;
   out_5041486069102284639[10] = 0;
   out_5041486069102284639[11] = 0;
   out_5041486069102284639[12] = 0;
   out_5041486069102284639[13] = 0;
   out_5041486069102284639[14] = 1;
   out_5041486069102284639[15] = 0;
   out_5041486069102284639[16] = 0;
   out_5041486069102284639[17] = 0;
}
void h_30(double *state, double *unused, double *out_860382997630719906) {
   out_860382997630719906[0] = state[4];
}
void H_30(double *state, double *unused, double *out_8714275447094518784) {
   out_8714275447094518784[0] = 0;
   out_8714275447094518784[1] = 0;
   out_8714275447094518784[2] = 0;
   out_8714275447094518784[3] = 0;
   out_8714275447094518784[4] = 1;
   out_8714275447094518784[5] = 0;
   out_8714275447094518784[6] = 0;
   out_8714275447094518784[7] = 0;
   out_8714275447094518784[8] = 0;
}
void h_26(double *state, double *unused, double *out_5538658519783129240) {
   out_5538658519783129240[0] = state[7];
}
void H_26(double *state, double *unused, double *out_925725033750640147) {
   out_925725033750640147[0] = 0;
   out_925725033750640147[1] = 0;
   out_925725033750640147[2] = 0;
   out_925725033750640147[3] = 0;
   out_925725033750640147[4] = 0;
   out_925725033750640147[5] = 0;
   out_925725033750640147[6] = 0;
   out_925725033750640147[7] = 1;
   out_925725033750640147[8] = 0;
}
void h_27(double *state, double *unused, double *out_2079086912816888230) {
   out_2079086912816888230[0] = state[3];
}
void H_27(double *state, double *unused, double *out_7557705314814607921) {
   out_7557705314814607921[0] = 0;
   out_7557705314814607921[1] = 0;
   out_7557705314814607921[2] = 0;
   out_7557705314814607921[3] = 1;
   out_7557705314814607921[4] = 0;
   out_7557705314814607921[5] = 0;
   out_7557705314814607921[6] = 0;
   out_7557705314814607921[7] = 0;
   out_7557705314814607921[8] = 0;
}
void h_29(double *state, double *unused, double *out_4141290270030125739) {
   out_4141290270030125739[0] = state[1];
}
void H_29(double *state, double *unused, double *out_8204044102780126600) {
   out_8204044102780126600[0] = 0;
   out_8204044102780126600[1] = 1;
   out_8204044102780126600[2] = 0;
   out_8204044102780126600[3] = 0;
   out_8204044102780126600[4] = 0;
   out_8204044102780126600[5] = 0;
   out_8204044102780126600[6] = 0;
   out_8204044102780126600[7] = 0;
   out_8204044102780126600[8] = 0;
}
void h_28(double *state, double *unused, double *out_4683492233625585881) {
   out_4683492233625585881[0] = state[0];
}
void H_28(double *state, double *unused, double *out_5160300953859894442) {
   out_5160300953859894442[0] = 1;
   out_5160300953859894442[1] = 0;
   out_5160300953859894442[2] = 0;
   out_5160300953859894442[3] = 0;
   out_5160300953859894442[4] = 0;
   out_5160300953859894442[5] = 0;
   out_5160300953859894442[6] = 0;
   out_5160300953859894442[7] = 0;
   out_5160300953859894442[8] = 0;
}
void h_31(double *state, double *unused, double *out_7504300416803316089) {
   out_7504300416803316089[0] = state[8];
}
void H_31(double *state, double *unused, double *out_2846424247000376505) {
   out_2846424247000376505[0] = 0;
   out_2846424247000376505[1] = 0;
   out_2846424247000376505[2] = 0;
   out_2846424247000376505[3] = 0;
   out_2846424247000376505[4] = 0;
   out_2846424247000376505[5] = 0;
   out_2846424247000376505[6] = 0;
   out_2846424247000376505[7] = 0;
   out_2846424247000376505[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_2769656543589876252) {
  err_fun(nom_x, delta_x, out_2769656543589876252);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_6259280918951514600) {
  inv_err_fun(nom_x, true_x, out_6259280918951514600);
}
void car_H_mod_fun(double *state, double *out_6437777562673898302) {
  H_mod_fun(state, out_6437777562673898302);
}
void car_f_fun(double *state, double dt, double *out_1051826260233084185) {
  f_fun(state,  dt, out_1051826260233084185);
}
void car_F_fun(double *state, double dt, double *out_4665134552691392129) {
  F_fun(state,  dt, out_4665134552691392129);
}
void car_h_25(double *state, double *unused, double *out_6902882259189952535) {
  h_25(state, unused, out_6902882259189952535);
}
void car_H_25(double *state, double *unused, double *out_2815778285123416077) {
  H_25(state, unused, out_2815778285123416077);
}
void car_h_24(double *state, double *unused, double *out_4770294784793454035) {
  h_24(state, unused, out_4770294784793454035);
}
void car_H_24(double *state, double *unused, double *out_5041486069102284639) {
  H_24(state, unused, out_5041486069102284639);
}
void car_h_30(double *state, double *unused, double *out_860382997630719906) {
  h_30(state, unused, out_860382997630719906);
}
void car_H_30(double *state, double *unused, double *out_8714275447094518784) {
  H_30(state, unused, out_8714275447094518784);
}
void car_h_26(double *state, double *unused, double *out_5538658519783129240) {
  h_26(state, unused, out_5538658519783129240);
}
void car_H_26(double *state, double *unused, double *out_925725033750640147) {
  H_26(state, unused, out_925725033750640147);
}
void car_h_27(double *state, double *unused, double *out_2079086912816888230) {
  h_27(state, unused, out_2079086912816888230);
}
void car_H_27(double *state, double *unused, double *out_7557705314814607921) {
  H_27(state, unused, out_7557705314814607921);
}
void car_h_29(double *state, double *unused, double *out_4141290270030125739) {
  h_29(state, unused, out_4141290270030125739);
}
void car_H_29(double *state, double *unused, double *out_8204044102780126600) {
  H_29(state, unused, out_8204044102780126600);
}
void car_h_28(double *state, double *unused, double *out_4683492233625585881) {
  h_28(state, unused, out_4683492233625585881);
}
void car_H_28(double *state, double *unused, double *out_5160300953859894442) {
  H_28(state, unused, out_5160300953859894442);
}
void car_h_31(double *state, double *unused, double *out_7504300416803316089) {
  h_31(state, unused, out_7504300416803316089);
}
void car_H_31(double *state, double *unused, double *out_2846424247000376505) {
  H_31(state, unused, out_2846424247000376505);
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
