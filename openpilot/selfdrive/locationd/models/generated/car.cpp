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
void err_fun(double *nom_x, double *delta_x, double *out_3709339290753435113) {
   out_3709339290753435113[0] = delta_x[0] + nom_x[0];
   out_3709339290753435113[1] = delta_x[1] + nom_x[1];
   out_3709339290753435113[2] = delta_x[2] + nom_x[2];
   out_3709339290753435113[3] = delta_x[3] + nom_x[3];
   out_3709339290753435113[4] = delta_x[4] + nom_x[4];
   out_3709339290753435113[5] = delta_x[5] + nom_x[5];
   out_3709339290753435113[6] = delta_x[6] + nom_x[6];
   out_3709339290753435113[7] = delta_x[7] + nom_x[7];
   out_3709339290753435113[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_2695906871061935165) {
   out_2695906871061935165[0] = -nom_x[0] + true_x[0];
   out_2695906871061935165[1] = -nom_x[1] + true_x[1];
   out_2695906871061935165[2] = -nom_x[2] + true_x[2];
   out_2695906871061935165[3] = -nom_x[3] + true_x[3];
   out_2695906871061935165[4] = -nom_x[4] + true_x[4];
   out_2695906871061935165[5] = -nom_x[5] + true_x[5];
   out_2695906871061935165[6] = -nom_x[6] + true_x[6];
   out_2695906871061935165[7] = -nom_x[7] + true_x[7];
   out_2695906871061935165[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_7521025143252519554) {
   out_7521025143252519554[0] = 1.0;
   out_7521025143252519554[1] = 0.0;
   out_7521025143252519554[2] = 0.0;
   out_7521025143252519554[3] = 0.0;
   out_7521025143252519554[4] = 0.0;
   out_7521025143252519554[5] = 0.0;
   out_7521025143252519554[6] = 0.0;
   out_7521025143252519554[7] = 0.0;
   out_7521025143252519554[8] = 0.0;
   out_7521025143252519554[9] = 0.0;
   out_7521025143252519554[10] = 1.0;
   out_7521025143252519554[11] = 0.0;
   out_7521025143252519554[12] = 0.0;
   out_7521025143252519554[13] = 0.0;
   out_7521025143252519554[14] = 0.0;
   out_7521025143252519554[15] = 0.0;
   out_7521025143252519554[16] = 0.0;
   out_7521025143252519554[17] = 0.0;
   out_7521025143252519554[18] = 0.0;
   out_7521025143252519554[19] = 0.0;
   out_7521025143252519554[20] = 1.0;
   out_7521025143252519554[21] = 0.0;
   out_7521025143252519554[22] = 0.0;
   out_7521025143252519554[23] = 0.0;
   out_7521025143252519554[24] = 0.0;
   out_7521025143252519554[25] = 0.0;
   out_7521025143252519554[26] = 0.0;
   out_7521025143252519554[27] = 0.0;
   out_7521025143252519554[28] = 0.0;
   out_7521025143252519554[29] = 0.0;
   out_7521025143252519554[30] = 1.0;
   out_7521025143252519554[31] = 0.0;
   out_7521025143252519554[32] = 0.0;
   out_7521025143252519554[33] = 0.0;
   out_7521025143252519554[34] = 0.0;
   out_7521025143252519554[35] = 0.0;
   out_7521025143252519554[36] = 0.0;
   out_7521025143252519554[37] = 0.0;
   out_7521025143252519554[38] = 0.0;
   out_7521025143252519554[39] = 0.0;
   out_7521025143252519554[40] = 1.0;
   out_7521025143252519554[41] = 0.0;
   out_7521025143252519554[42] = 0.0;
   out_7521025143252519554[43] = 0.0;
   out_7521025143252519554[44] = 0.0;
   out_7521025143252519554[45] = 0.0;
   out_7521025143252519554[46] = 0.0;
   out_7521025143252519554[47] = 0.0;
   out_7521025143252519554[48] = 0.0;
   out_7521025143252519554[49] = 0.0;
   out_7521025143252519554[50] = 1.0;
   out_7521025143252519554[51] = 0.0;
   out_7521025143252519554[52] = 0.0;
   out_7521025143252519554[53] = 0.0;
   out_7521025143252519554[54] = 0.0;
   out_7521025143252519554[55] = 0.0;
   out_7521025143252519554[56] = 0.0;
   out_7521025143252519554[57] = 0.0;
   out_7521025143252519554[58] = 0.0;
   out_7521025143252519554[59] = 0.0;
   out_7521025143252519554[60] = 1.0;
   out_7521025143252519554[61] = 0.0;
   out_7521025143252519554[62] = 0.0;
   out_7521025143252519554[63] = 0.0;
   out_7521025143252519554[64] = 0.0;
   out_7521025143252519554[65] = 0.0;
   out_7521025143252519554[66] = 0.0;
   out_7521025143252519554[67] = 0.0;
   out_7521025143252519554[68] = 0.0;
   out_7521025143252519554[69] = 0.0;
   out_7521025143252519554[70] = 1.0;
   out_7521025143252519554[71] = 0.0;
   out_7521025143252519554[72] = 0.0;
   out_7521025143252519554[73] = 0.0;
   out_7521025143252519554[74] = 0.0;
   out_7521025143252519554[75] = 0.0;
   out_7521025143252519554[76] = 0.0;
   out_7521025143252519554[77] = 0.0;
   out_7521025143252519554[78] = 0.0;
   out_7521025143252519554[79] = 0.0;
   out_7521025143252519554[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_2870569988724221657) {
   out_2870569988724221657[0] = state[0];
   out_2870569988724221657[1] = state[1];
   out_2870569988724221657[2] = state[2];
   out_2870569988724221657[3] = state[3];
   out_2870569988724221657[4] = state[4];
   out_2870569988724221657[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_2870569988724221657[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_2870569988724221657[7] = state[7];
   out_2870569988724221657[8] = state[8];
}
void F_fun(double *state, double dt, double *out_1340125705655256792) {
   out_1340125705655256792[0] = 1;
   out_1340125705655256792[1] = 0;
   out_1340125705655256792[2] = 0;
   out_1340125705655256792[3] = 0;
   out_1340125705655256792[4] = 0;
   out_1340125705655256792[5] = 0;
   out_1340125705655256792[6] = 0;
   out_1340125705655256792[7] = 0;
   out_1340125705655256792[8] = 0;
   out_1340125705655256792[9] = 0;
   out_1340125705655256792[10] = 1;
   out_1340125705655256792[11] = 0;
   out_1340125705655256792[12] = 0;
   out_1340125705655256792[13] = 0;
   out_1340125705655256792[14] = 0;
   out_1340125705655256792[15] = 0;
   out_1340125705655256792[16] = 0;
   out_1340125705655256792[17] = 0;
   out_1340125705655256792[18] = 0;
   out_1340125705655256792[19] = 0;
   out_1340125705655256792[20] = 1;
   out_1340125705655256792[21] = 0;
   out_1340125705655256792[22] = 0;
   out_1340125705655256792[23] = 0;
   out_1340125705655256792[24] = 0;
   out_1340125705655256792[25] = 0;
   out_1340125705655256792[26] = 0;
   out_1340125705655256792[27] = 0;
   out_1340125705655256792[28] = 0;
   out_1340125705655256792[29] = 0;
   out_1340125705655256792[30] = 1;
   out_1340125705655256792[31] = 0;
   out_1340125705655256792[32] = 0;
   out_1340125705655256792[33] = 0;
   out_1340125705655256792[34] = 0;
   out_1340125705655256792[35] = 0;
   out_1340125705655256792[36] = 0;
   out_1340125705655256792[37] = 0;
   out_1340125705655256792[38] = 0;
   out_1340125705655256792[39] = 0;
   out_1340125705655256792[40] = 1;
   out_1340125705655256792[41] = 0;
   out_1340125705655256792[42] = 0;
   out_1340125705655256792[43] = 0;
   out_1340125705655256792[44] = 0;
   out_1340125705655256792[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_1340125705655256792[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_1340125705655256792[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_1340125705655256792[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_1340125705655256792[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_1340125705655256792[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_1340125705655256792[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_1340125705655256792[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_1340125705655256792[53] = -9.8100000000000005*dt;
   out_1340125705655256792[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_1340125705655256792[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_1340125705655256792[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_1340125705655256792[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_1340125705655256792[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_1340125705655256792[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_1340125705655256792[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_1340125705655256792[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_1340125705655256792[62] = 0;
   out_1340125705655256792[63] = 0;
   out_1340125705655256792[64] = 0;
   out_1340125705655256792[65] = 0;
   out_1340125705655256792[66] = 0;
   out_1340125705655256792[67] = 0;
   out_1340125705655256792[68] = 0;
   out_1340125705655256792[69] = 0;
   out_1340125705655256792[70] = 1;
   out_1340125705655256792[71] = 0;
   out_1340125705655256792[72] = 0;
   out_1340125705655256792[73] = 0;
   out_1340125705655256792[74] = 0;
   out_1340125705655256792[75] = 0;
   out_1340125705655256792[76] = 0;
   out_1340125705655256792[77] = 0;
   out_1340125705655256792[78] = 0;
   out_1340125705655256792[79] = 0;
   out_1340125705655256792[80] = 1;
}
void h_25(double *state, double *unused, double *out_1820458384291824141) {
   out_1820458384291824141[0] = state[6];
}
void H_25(double *state, double *unused, double *out_2436349258228458819) {
   out_2436349258228458819[0] = 0;
   out_2436349258228458819[1] = 0;
   out_2436349258228458819[2] = 0;
   out_2436349258228458819[3] = 0;
   out_2436349258228458819[4] = 0;
   out_2436349258228458819[5] = 0;
   out_2436349258228458819[6] = 1;
   out_2436349258228458819[7] = 0;
   out_2436349258228458819[8] = 0;
}
void h_24(double *state, double *unused, double *out_809263190072562720) {
   out_809263190072562720[0] = state[4];
   out_809263190072562720[1] = state[5];
}
void H_24(double *state, double *unused, double *out_259134834621308846) {
   out_259134834621308846[0] = 0;
   out_259134834621308846[1] = 0;
   out_259134834621308846[2] = 0;
   out_259134834621308846[3] = 0;
   out_259134834621308846[4] = 1;
   out_259134834621308846[5] = 0;
   out_259134834621308846[6] = 0;
   out_259134834621308846[7] = 0;
   out_259134834621308846[8] = 0;
   out_259134834621308846[9] = 0;
   out_259134834621308846[10] = 0;
   out_259134834621308846[11] = 0;
   out_259134834621308846[12] = 0;
   out_259134834621308846[13] = 0;
   out_259134834621308846[14] = 1;
   out_259134834621308846[15] = 0;
   out_259134834621308846[16] = 0;
   out_259134834621308846[17] = 0;
}
void h_30(double *state, double *unused, double *out_3222422842442281109) {
   out_3222422842442281109[0] = state[4];
}
void H_30(double *state, double *unused, double *out_81983700278789808) {
   out_81983700278789808[0] = 0;
   out_81983700278789808[1] = 0;
   out_81983700278789808[2] = 0;
   out_81983700278789808[3] = 0;
   out_81983700278789808[4] = 1;
   out_81983700278789808[5] = 0;
   out_81983700278789808[6] = 0;
   out_81983700278789808[7] = 0;
   out_81983700278789808[8] = 0;
}
void h_26(double *state, double *unused, double *out_7423549809566033340) {
   out_7423549809566033340[0] = state[7];
}
void H_26(double *state, double *unused, double *out_868176711532341782) {
   out_868176711532341782[0] = 0;
   out_868176711532341782[1] = 0;
   out_868176711532341782[2] = 0;
   out_868176711532341782[3] = 0;
   out_868176711532341782[4] = 0;
   out_868176711532341782[5] = 0;
   out_868176711532341782[6] = 0;
   out_868176711532341782[7] = 1;
   out_868176711532341782[8] = 0;
}
void h_27(double *state, double *unused, double *out_1217142499615346624) {
   out_1217142499615346624[0] = state[3];
}
void H_27(double *state, double *unused, double *out_2092779611521635103) {
   out_2092779611521635103[0] = 0;
   out_2092779611521635103[1] = 0;
   out_2092779611521635103[2] = 0;
   out_2092779611521635103[3] = 1;
   out_2092779611521635103[4] = 0;
   out_2092779611521635103[5] = 0;
   out_2092779611521635103[6] = 0;
   out_2092779611521635103[7] = 0;
   out_2092779611521635103[8] = 0;
}
void h_29(double *state, double *unused, double *out_5602594215076499458) {
   out_5602594215076499458[0] = state[1];
}
void H_29(double *state, double *unused, double *out_592215044593181992) {
   out_592215044593181992[0] = 0;
   out_592215044593181992[1] = 1;
   out_592215044593181992[2] = 0;
   out_592215044593181992[3] = 0;
   out_592215044593181992[4] = 0;
   out_592215044593181992[5] = 0;
   out_592215044593181992[6] = 0;
   out_592215044593181992[7] = 0;
   out_592215044593181992[8] = 0;
}
void h_28(double *state, double *unused, double *out_6547692270471837786) {
   out_6547692270471837786[0] = state[0];
}
void H_28(double *state, double *unused, double *out_4490183972476348582) {
   out_4490183972476348582[0] = 1;
   out_4490183972476348582[1] = 0;
   out_4490183972476348582[2] = 0;
   out_4490183972476348582[3] = 0;
   out_4490183972476348582[4] = 0;
   out_4490183972476348582[5] = 0;
   out_4490183972476348582[6] = 0;
   out_4490183972476348582[7] = 0;
   out_4490183972476348582[8] = 0;
}
void h_31(double *state, double *unused, double *out_7005392194916958430) {
   out_7005392194916958430[0] = state[8];
}
void H_31(double *state, double *unused, double *out_241968609298990306) {
   out_241968609298990306[0] = 0;
   out_241968609298990306[1] = 0;
   out_241968609298990306[2] = 0;
   out_241968609298990306[3] = 0;
   out_241968609298990306[4] = 0;
   out_241968609298990306[5] = 0;
   out_241968609298990306[6] = 0;
   out_241968609298990306[7] = 0;
   out_241968609298990306[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_3709339290753435113) {
  err_fun(nom_x, delta_x, out_3709339290753435113);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_2695906871061935165) {
  inv_err_fun(nom_x, true_x, out_2695906871061935165);
}
void car_H_mod_fun(double *state, double *out_7521025143252519554) {
  H_mod_fun(state, out_7521025143252519554);
}
void car_f_fun(double *state, double dt, double *out_2870569988724221657) {
  f_fun(state,  dt, out_2870569988724221657);
}
void car_F_fun(double *state, double dt, double *out_1340125705655256792) {
  F_fun(state,  dt, out_1340125705655256792);
}
void car_h_25(double *state, double *unused, double *out_1820458384291824141) {
  h_25(state, unused, out_1820458384291824141);
}
void car_H_25(double *state, double *unused, double *out_2436349258228458819) {
  H_25(state, unused, out_2436349258228458819);
}
void car_h_24(double *state, double *unused, double *out_809263190072562720) {
  h_24(state, unused, out_809263190072562720);
}
void car_H_24(double *state, double *unused, double *out_259134834621308846) {
  H_24(state, unused, out_259134834621308846);
}
void car_h_30(double *state, double *unused, double *out_3222422842442281109) {
  h_30(state, unused, out_3222422842442281109);
}
void car_H_30(double *state, double *unused, double *out_81983700278789808) {
  H_30(state, unused, out_81983700278789808);
}
void car_h_26(double *state, double *unused, double *out_7423549809566033340) {
  h_26(state, unused, out_7423549809566033340);
}
void car_H_26(double *state, double *unused, double *out_868176711532341782) {
  H_26(state, unused, out_868176711532341782);
}
void car_h_27(double *state, double *unused, double *out_1217142499615346624) {
  h_27(state, unused, out_1217142499615346624);
}
void car_H_27(double *state, double *unused, double *out_2092779611521635103) {
  H_27(state, unused, out_2092779611521635103);
}
void car_h_29(double *state, double *unused, double *out_5602594215076499458) {
  h_29(state, unused, out_5602594215076499458);
}
void car_H_29(double *state, double *unused, double *out_592215044593181992) {
  H_29(state, unused, out_592215044593181992);
}
void car_h_28(double *state, double *unused, double *out_6547692270471837786) {
  h_28(state, unused, out_6547692270471837786);
}
void car_H_28(double *state, double *unused, double *out_4490183972476348582) {
  H_28(state, unused, out_4490183972476348582);
}
void car_h_31(double *state, double *unused, double *out_7005392194916958430) {
  h_31(state, unused, out_7005392194916958430);
}
void car_H_31(double *state, double *unused, double *out_241968609298990306) {
  H_31(state, unused, out_241968609298990306);
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
