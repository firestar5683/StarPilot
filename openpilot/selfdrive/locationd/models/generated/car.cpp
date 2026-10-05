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
void err_fun(double *nom_x, double *delta_x, double *out_3469758484501884827) {
   out_3469758484501884827[0] = delta_x[0] + nom_x[0];
   out_3469758484501884827[1] = delta_x[1] + nom_x[1];
   out_3469758484501884827[2] = delta_x[2] + nom_x[2];
   out_3469758484501884827[3] = delta_x[3] + nom_x[3];
   out_3469758484501884827[4] = delta_x[4] + nom_x[4];
   out_3469758484501884827[5] = delta_x[5] + nom_x[5];
   out_3469758484501884827[6] = delta_x[6] + nom_x[6];
   out_3469758484501884827[7] = delta_x[7] + nom_x[7];
   out_3469758484501884827[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_4255984246366508924) {
   out_4255984246366508924[0] = -nom_x[0] + true_x[0];
   out_4255984246366508924[1] = -nom_x[1] + true_x[1];
   out_4255984246366508924[2] = -nom_x[2] + true_x[2];
   out_4255984246366508924[3] = -nom_x[3] + true_x[3];
   out_4255984246366508924[4] = -nom_x[4] + true_x[4];
   out_4255984246366508924[5] = -nom_x[5] + true_x[5];
   out_4255984246366508924[6] = -nom_x[6] + true_x[6];
   out_4255984246366508924[7] = -nom_x[7] + true_x[7];
   out_4255984246366508924[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_838313629168922668) {
   out_838313629168922668[0] = 1.0;
   out_838313629168922668[1] = 0.0;
   out_838313629168922668[2] = 0.0;
   out_838313629168922668[3] = 0.0;
   out_838313629168922668[4] = 0.0;
   out_838313629168922668[5] = 0.0;
   out_838313629168922668[6] = 0.0;
   out_838313629168922668[7] = 0.0;
   out_838313629168922668[8] = 0.0;
   out_838313629168922668[9] = 0.0;
   out_838313629168922668[10] = 1.0;
   out_838313629168922668[11] = 0.0;
   out_838313629168922668[12] = 0.0;
   out_838313629168922668[13] = 0.0;
   out_838313629168922668[14] = 0.0;
   out_838313629168922668[15] = 0.0;
   out_838313629168922668[16] = 0.0;
   out_838313629168922668[17] = 0.0;
   out_838313629168922668[18] = 0.0;
   out_838313629168922668[19] = 0.0;
   out_838313629168922668[20] = 1.0;
   out_838313629168922668[21] = 0.0;
   out_838313629168922668[22] = 0.0;
   out_838313629168922668[23] = 0.0;
   out_838313629168922668[24] = 0.0;
   out_838313629168922668[25] = 0.0;
   out_838313629168922668[26] = 0.0;
   out_838313629168922668[27] = 0.0;
   out_838313629168922668[28] = 0.0;
   out_838313629168922668[29] = 0.0;
   out_838313629168922668[30] = 1.0;
   out_838313629168922668[31] = 0.0;
   out_838313629168922668[32] = 0.0;
   out_838313629168922668[33] = 0.0;
   out_838313629168922668[34] = 0.0;
   out_838313629168922668[35] = 0.0;
   out_838313629168922668[36] = 0.0;
   out_838313629168922668[37] = 0.0;
   out_838313629168922668[38] = 0.0;
   out_838313629168922668[39] = 0.0;
   out_838313629168922668[40] = 1.0;
   out_838313629168922668[41] = 0.0;
   out_838313629168922668[42] = 0.0;
   out_838313629168922668[43] = 0.0;
   out_838313629168922668[44] = 0.0;
   out_838313629168922668[45] = 0.0;
   out_838313629168922668[46] = 0.0;
   out_838313629168922668[47] = 0.0;
   out_838313629168922668[48] = 0.0;
   out_838313629168922668[49] = 0.0;
   out_838313629168922668[50] = 1.0;
   out_838313629168922668[51] = 0.0;
   out_838313629168922668[52] = 0.0;
   out_838313629168922668[53] = 0.0;
   out_838313629168922668[54] = 0.0;
   out_838313629168922668[55] = 0.0;
   out_838313629168922668[56] = 0.0;
   out_838313629168922668[57] = 0.0;
   out_838313629168922668[58] = 0.0;
   out_838313629168922668[59] = 0.0;
   out_838313629168922668[60] = 1.0;
   out_838313629168922668[61] = 0.0;
   out_838313629168922668[62] = 0.0;
   out_838313629168922668[63] = 0.0;
   out_838313629168922668[64] = 0.0;
   out_838313629168922668[65] = 0.0;
   out_838313629168922668[66] = 0.0;
   out_838313629168922668[67] = 0.0;
   out_838313629168922668[68] = 0.0;
   out_838313629168922668[69] = 0.0;
   out_838313629168922668[70] = 1.0;
   out_838313629168922668[71] = 0.0;
   out_838313629168922668[72] = 0.0;
   out_838313629168922668[73] = 0.0;
   out_838313629168922668[74] = 0.0;
   out_838313629168922668[75] = 0.0;
   out_838313629168922668[76] = 0.0;
   out_838313629168922668[77] = 0.0;
   out_838313629168922668[78] = 0.0;
   out_838313629168922668[79] = 0.0;
   out_838313629168922668[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_3973498408852423807) {
   out_3973498408852423807[0] = state[0];
   out_3973498408852423807[1] = state[1];
   out_3973498408852423807[2] = state[2];
   out_3973498408852423807[3] = state[3];
   out_3973498408852423807[4] = state[4];
   out_3973498408852423807[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_3973498408852423807[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_3973498408852423807[7] = state[7];
   out_3973498408852423807[8] = state[8];
}
void F_fun(double *state, double dt, double *out_6994900003842630149) {
   out_6994900003842630149[0] = 1;
   out_6994900003842630149[1] = 0;
   out_6994900003842630149[2] = 0;
   out_6994900003842630149[3] = 0;
   out_6994900003842630149[4] = 0;
   out_6994900003842630149[5] = 0;
   out_6994900003842630149[6] = 0;
   out_6994900003842630149[7] = 0;
   out_6994900003842630149[8] = 0;
   out_6994900003842630149[9] = 0;
   out_6994900003842630149[10] = 1;
   out_6994900003842630149[11] = 0;
   out_6994900003842630149[12] = 0;
   out_6994900003842630149[13] = 0;
   out_6994900003842630149[14] = 0;
   out_6994900003842630149[15] = 0;
   out_6994900003842630149[16] = 0;
   out_6994900003842630149[17] = 0;
   out_6994900003842630149[18] = 0;
   out_6994900003842630149[19] = 0;
   out_6994900003842630149[20] = 1;
   out_6994900003842630149[21] = 0;
   out_6994900003842630149[22] = 0;
   out_6994900003842630149[23] = 0;
   out_6994900003842630149[24] = 0;
   out_6994900003842630149[25] = 0;
   out_6994900003842630149[26] = 0;
   out_6994900003842630149[27] = 0;
   out_6994900003842630149[28] = 0;
   out_6994900003842630149[29] = 0;
   out_6994900003842630149[30] = 1;
   out_6994900003842630149[31] = 0;
   out_6994900003842630149[32] = 0;
   out_6994900003842630149[33] = 0;
   out_6994900003842630149[34] = 0;
   out_6994900003842630149[35] = 0;
   out_6994900003842630149[36] = 0;
   out_6994900003842630149[37] = 0;
   out_6994900003842630149[38] = 0;
   out_6994900003842630149[39] = 0;
   out_6994900003842630149[40] = 1;
   out_6994900003842630149[41] = 0;
   out_6994900003842630149[42] = 0;
   out_6994900003842630149[43] = 0;
   out_6994900003842630149[44] = 0;
   out_6994900003842630149[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_6994900003842630149[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_6994900003842630149[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_6994900003842630149[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_6994900003842630149[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_6994900003842630149[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_6994900003842630149[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_6994900003842630149[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_6994900003842630149[53] = -9.8100000000000005*dt;
   out_6994900003842630149[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_6994900003842630149[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_6994900003842630149[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_6994900003842630149[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_6994900003842630149[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_6994900003842630149[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_6994900003842630149[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_6994900003842630149[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_6994900003842630149[62] = 0;
   out_6994900003842630149[63] = 0;
   out_6994900003842630149[64] = 0;
   out_6994900003842630149[65] = 0;
   out_6994900003842630149[66] = 0;
   out_6994900003842630149[67] = 0;
   out_6994900003842630149[68] = 0;
   out_6994900003842630149[69] = 0;
   out_6994900003842630149[70] = 1;
   out_6994900003842630149[71] = 0;
   out_6994900003842630149[72] = 0;
   out_6994900003842630149[73] = 0;
   out_6994900003842630149[74] = 0;
   out_6994900003842630149[75] = 0;
   out_6994900003842630149[76] = 0;
   out_6994900003842630149[77] = 0;
   out_6994900003842630149[78] = 0;
   out_6994900003842630149[79] = 0;
   out_6994900003842630149[80] = 1;
}
void h_25(double *state, double *unused, double *out_6334052399702442592) {
   out_6334052399702442592[0] = state[6];
}
void H_25(double *state, double *unused, double *out_7083024403804937137) {
   out_7083024403804937137[0] = 0;
   out_7083024403804937137[1] = 0;
   out_7083024403804937137[2] = 0;
   out_7083024403804937137[3] = 0;
   out_7083024403804937137[4] = 0;
   out_7083024403804937137[5] = 0;
   out_7083024403804937137[6] = 1;
   out_7083024403804937137[7] = 0;
   out_7083024403804937137[8] = 0;
}
void h_24(double *state, double *unused, double *out_9073812845593672478) {
   out_9073812845593672478[0] = state[4];
   out_9073812845593672478[1] = state[5];
}
void H_24(double *state, double *unused, double *out_2336515076838428103) {
   out_2336515076838428103[0] = 0;
   out_2336515076838428103[1] = 0;
   out_2336515076838428103[2] = 0;
   out_2336515076838428103[3] = 0;
   out_2336515076838428103[4] = 1;
   out_2336515076838428103[5] = 0;
   out_2336515076838428103[6] = 0;
   out_2336515076838428103[7] = 0;
   out_2336515076838428103[8] = 0;
   out_2336515076838428103[9] = 0;
   out_2336515076838428103[10] = 0;
   out_2336515076838428103[11] = 0;
   out_2336515076838428103[12] = 0;
   out_2336515076838428103[13] = 0;
   out_2336515076838428103[14] = 1;
   out_2336515076838428103[15] = 0;
   out_2336515076838428103[16] = 0;
   out_2336515076838428103[17] = 0;
}
void h_30(double *state, double *unused, double *out_436782826647908344) {
   out_436782826647908344[0] = state[4];
}
void H_30(double *state, double *unused, double *out_8845386711397365852) {
   out_8845386711397365852[0] = 0;
   out_8845386711397365852[1] = 0;
   out_8845386711397365852[2] = 0;
   out_8845386711397365852[3] = 0;
   out_8845386711397365852[4] = 1;
   out_8845386711397365852[5] = 0;
   out_8845386711397365852[6] = 0;
   out_8845386711397365852[7] = 0;
   out_8845386711397365852[8] = 0;
}
void h_26(double *state, double *unused, double *out_2167622494160789307) {
   out_2167622494160789307[0] = state[7];
}
void H_26(double *state, double *unused, double *out_3341521084930880913) {
   out_3341521084930880913[0] = 0;
   out_3341521084930880913[1] = 0;
   out_3341521084930880913[2] = 0;
   out_3341521084930880913[3] = 0;
   out_3341521084930880913[4] = 0;
   out_3341521084930880913[5] = 0;
   out_3341521084930880913[6] = 0;
   out_3341521084930880913[7] = 1;
   out_3341521084930880913[8] = 0;
}
void h_27(double *state, double *unused, double *out_992185163816412029) {
   out_992185163816412029[0] = state[3];
}
void H_27(double *state, double *unused, double *out_6621792640213422635) {
   out_6621792640213422635[0] = 0;
   out_6621792640213422635[1] = 0;
   out_6621792640213422635[2] = 0;
   out_6621792640213422635[3] = 1;
   out_6621792640213422635[4] = 0;
   out_6621792640213422635[5] = 0;
   out_6621792640213422635[6] = 0;
   out_6621792640213422635[7] = 0;
   out_6621792640213422635[8] = 0;
}
void h_29(double *state, double *unused, double *out_5174928876154722274) {
   out_5174928876154722274[0] = state[1];
}
void H_29(double *state, double *unused, double *out_8335155367082973668) {
   out_8335155367082973668[0] = 0;
   out_8335155367082973668[1] = 1;
   out_8335155367082973668[2] = 0;
   out_8335155367082973668[3] = 0;
   out_8335155367082973668[4] = 0;
   out_8335155367082973668[5] = 0;
   out_8335155367082973668[6] = 0;
   out_8335155367082973668[7] = 0;
   out_8335155367082973668[8] = 0;
}
void h_28(double *state, double *unused, double *out_5993858431477257674) {
   out_5993858431477257674[0] = state[0];
}
void H_28(double *state, double *unused, double *out_5029189689557047374) {
   out_5029189689557047374[0] = 1;
   out_5029189689557047374[1] = 0;
   out_5029189689557047374[2] = 0;
   out_5029189689557047374[3] = 0;
   out_5029189689557047374[4] = 0;
   out_5029189689557047374[5] = 0;
   out_5029189689557047374[6] = 0;
   out_5029189689557047374[7] = 0;
   out_5029189689557047374[8] = 0;
}
void h_31(double *state, double *unused, double *out_8152134535960606953) {
   out_8152134535960606953[0] = state[8];
}
void H_31(double *state, double *unused, double *out_2715312982697529437) {
   out_2715312982697529437[0] = 0;
   out_2715312982697529437[1] = 0;
   out_2715312982697529437[2] = 0;
   out_2715312982697529437[3] = 0;
   out_2715312982697529437[4] = 0;
   out_2715312982697529437[5] = 0;
   out_2715312982697529437[6] = 0;
   out_2715312982697529437[7] = 0;
   out_2715312982697529437[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_3469758484501884827) {
  err_fun(nom_x, delta_x, out_3469758484501884827);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_4255984246366508924) {
  inv_err_fun(nom_x, true_x, out_4255984246366508924);
}
void car_H_mod_fun(double *state, double *out_838313629168922668) {
  H_mod_fun(state, out_838313629168922668);
}
void car_f_fun(double *state, double dt, double *out_3973498408852423807) {
  f_fun(state,  dt, out_3973498408852423807);
}
void car_F_fun(double *state, double dt, double *out_6994900003842630149) {
  F_fun(state,  dt, out_6994900003842630149);
}
void car_h_25(double *state, double *unused, double *out_6334052399702442592) {
  h_25(state, unused, out_6334052399702442592);
}
void car_H_25(double *state, double *unused, double *out_7083024403804937137) {
  H_25(state, unused, out_7083024403804937137);
}
void car_h_24(double *state, double *unused, double *out_9073812845593672478) {
  h_24(state, unused, out_9073812845593672478);
}
void car_H_24(double *state, double *unused, double *out_2336515076838428103) {
  H_24(state, unused, out_2336515076838428103);
}
void car_h_30(double *state, double *unused, double *out_436782826647908344) {
  h_30(state, unused, out_436782826647908344);
}
void car_H_30(double *state, double *unused, double *out_8845386711397365852) {
  H_30(state, unused, out_8845386711397365852);
}
void car_h_26(double *state, double *unused, double *out_2167622494160789307) {
  h_26(state, unused, out_2167622494160789307);
}
void car_H_26(double *state, double *unused, double *out_3341521084930880913) {
  H_26(state, unused, out_3341521084930880913);
}
void car_h_27(double *state, double *unused, double *out_992185163816412029) {
  h_27(state, unused, out_992185163816412029);
}
void car_H_27(double *state, double *unused, double *out_6621792640213422635) {
  H_27(state, unused, out_6621792640213422635);
}
void car_h_29(double *state, double *unused, double *out_5174928876154722274) {
  h_29(state, unused, out_5174928876154722274);
}
void car_H_29(double *state, double *unused, double *out_8335155367082973668) {
  H_29(state, unused, out_8335155367082973668);
}
void car_h_28(double *state, double *unused, double *out_5993858431477257674) {
  h_28(state, unused, out_5993858431477257674);
}
void car_H_28(double *state, double *unused, double *out_5029189689557047374) {
  H_28(state, unused, out_5029189689557047374);
}
void car_h_31(double *state, double *unused, double *out_8152134535960606953) {
  h_31(state, unused, out_8152134535960606953);
}
void car_H_31(double *state, double *unused, double *out_2715312982697529437) {
  H_31(state, unused, out_2715312982697529437);
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
