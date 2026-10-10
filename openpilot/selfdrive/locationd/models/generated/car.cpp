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
void err_fun(double *nom_x, double *delta_x, double *out_3194710944048673507) {
   out_3194710944048673507[0] = delta_x[0] + nom_x[0];
   out_3194710944048673507[1] = delta_x[1] + nom_x[1];
   out_3194710944048673507[2] = delta_x[2] + nom_x[2];
   out_3194710944048673507[3] = delta_x[3] + nom_x[3];
   out_3194710944048673507[4] = delta_x[4] + nom_x[4];
   out_3194710944048673507[5] = delta_x[5] + nom_x[5];
   out_3194710944048673507[6] = delta_x[6] + nom_x[6];
   out_3194710944048673507[7] = delta_x[7] + nom_x[7];
   out_3194710944048673507[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_8039664853018696099) {
   out_8039664853018696099[0] = -nom_x[0] + true_x[0];
   out_8039664853018696099[1] = -nom_x[1] + true_x[1];
   out_8039664853018696099[2] = -nom_x[2] + true_x[2];
   out_8039664853018696099[3] = -nom_x[3] + true_x[3];
   out_8039664853018696099[4] = -nom_x[4] + true_x[4];
   out_8039664853018696099[5] = -nom_x[5] + true_x[5];
   out_8039664853018696099[6] = -nom_x[6] + true_x[6];
   out_8039664853018696099[7] = -nom_x[7] + true_x[7];
   out_8039664853018696099[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_5587385678613239193) {
   out_5587385678613239193[0] = 1.0;
   out_5587385678613239193[1] = 0.0;
   out_5587385678613239193[2] = 0.0;
   out_5587385678613239193[3] = 0.0;
   out_5587385678613239193[4] = 0.0;
   out_5587385678613239193[5] = 0.0;
   out_5587385678613239193[6] = 0.0;
   out_5587385678613239193[7] = 0.0;
   out_5587385678613239193[8] = 0.0;
   out_5587385678613239193[9] = 0.0;
   out_5587385678613239193[10] = 1.0;
   out_5587385678613239193[11] = 0.0;
   out_5587385678613239193[12] = 0.0;
   out_5587385678613239193[13] = 0.0;
   out_5587385678613239193[14] = 0.0;
   out_5587385678613239193[15] = 0.0;
   out_5587385678613239193[16] = 0.0;
   out_5587385678613239193[17] = 0.0;
   out_5587385678613239193[18] = 0.0;
   out_5587385678613239193[19] = 0.0;
   out_5587385678613239193[20] = 1.0;
   out_5587385678613239193[21] = 0.0;
   out_5587385678613239193[22] = 0.0;
   out_5587385678613239193[23] = 0.0;
   out_5587385678613239193[24] = 0.0;
   out_5587385678613239193[25] = 0.0;
   out_5587385678613239193[26] = 0.0;
   out_5587385678613239193[27] = 0.0;
   out_5587385678613239193[28] = 0.0;
   out_5587385678613239193[29] = 0.0;
   out_5587385678613239193[30] = 1.0;
   out_5587385678613239193[31] = 0.0;
   out_5587385678613239193[32] = 0.0;
   out_5587385678613239193[33] = 0.0;
   out_5587385678613239193[34] = 0.0;
   out_5587385678613239193[35] = 0.0;
   out_5587385678613239193[36] = 0.0;
   out_5587385678613239193[37] = 0.0;
   out_5587385678613239193[38] = 0.0;
   out_5587385678613239193[39] = 0.0;
   out_5587385678613239193[40] = 1.0;
   out_5587385678613239193[41] = 0.0;
   out_5587385678613239193[42] = 0.0;
   out_5587385678613239193[43] = 0.0;
   out_5587385678613239193[44] = 0.0;
   out_5587385678613239193[45] = 0.0;
   out_5587385678613239193[46] = 0.0;
   out_5587385678613239193[47] = 0.0;
   out_5587385678613239193[48] = 0.0;
   out_5587385678613239193[49] = 0.0;
   out_5587385678613239193[50] = 1.0;
   out_5587385678613239193[51] = 0.0;
   out_5587385678613239193[52] = 0.0;
   out_5587385678613239193[53] = 0.0;
   out_5587385678613239193[54] = 0.0;
   out_5587385678613239193[55] = 0.0;
   out_5587385678613239193[56] = 0.0;
   out_5587385678613239193[57] = 0.0;
   out_5587385678613239193[58] = 0.0;
   out_5587385678613239193[59] = 0.0;
   out_5587385678613239193[60] = 1.0;
   out_5587385678613239193[61] = 0.0;
   out_5587385678613239193[62] = 0.0;
   out_5587385678613239193[63] = 0.0;
   out_5587385678613239193[64] = 0.0;
   out_5587385678613239193[65] = 0.0;
   out_5587385678613239193[66] = 0.0;
   out_5587385678613239193[67] = 0.0;
   out_5587385678613239193[68] = 0.0;
   out_5587385678613239193[69] = 0.0;
   out_5587385678613239193[70] = 1.0;
   out_5587385678613239193[71] = 0.0;
   out_5587385678613239193[72] = 0.0;
   out_5587385678613239193[73] = 0.0;
   out_5587385678613239193[74] = 0.0;
   out_5587385678613239193[75] = 0.0;
   out_5587385678613239193[76] = 0.0;
   out_5587385678613239193[77] = 0.0;
   out_5587385678613239193[78] = 0.0;
   out_5587385678613239193[79] = 0.0;
   out_5587385678613239193[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_7292828168458319052) {
   out_7292828168458319052[0] = state[0];
   out_7292828168458319052[1] = state[1];
   out_7292828168458319052[2] = state[2];
   out_7292828168458319052[3] = state[3];
   out_7292828168458319052[4] = state[4];
   out_7292828168458319052[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_7292828168458319052[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_7292828168458319052[7] = state[7];
   out_7292828168458319052[8] = state[8];
}
void F_fun(double *state, double dt, double *out_2978169847506375272) {
   out_2978169847506375272[0] = 1;
   out_2978169847506375272[1] = 0;
   out_2978169847506375272[2] = 0;
   out_2978169847506375272[3] = 0;
   out_2978169847506375272[4] = 0;
   out_2978169847506375272[5] = 0;
   out_2978169847506375272[6] = 0;
   out_2978169847506375272[7] = 0;
   out_2978169847506375272[8] = 0;
   out_2978169847506375272[9] = 0;
   out_2978169847506375272[10] = 1;
   out_2978169847506375272[11] = 0;
   out_2978169847506375272[12] = 0;
   out_2978169847506375272[13] = 0;
   out_2978169847506375272[14] = 0;
   out_2978169847506375272[15] = 0;
   out_2978169847506375272[16] = 0;
   out_2978169847506375272[17] = 0;
   out_2978169847506375272[18] = 0;
   out_2978169847506375272[19] = 0;
   out_2978169847506375272[20] = 1;
   out_2978169847506375272[21] = 0;
   out_2978169847506375272[22] = 0;
   out_2978169847506375272[23] = 0;
   out_2978169847506375272[24] = 0;
   out_2978169847506375272[25] = 0;
   out_2978169847506375272[26] = 0;
   out_2978169847506375272[27] = 0;
   out_2978169847506375272[28] = 0;
   out_2978169847506375272[29] = 0;
   out_2978169847506375272[30] = 1;
   out_2978169847506375272[31] = 0;
   out_2978169847506375272[32] = 0;
   out_2978169847506375272[33] = 0;
   out_2978169847506375272[34] = 0;
   out_2978169847506375272[35] = 0;
   out_2978169847506375272[36] = 0;
   out_2978169847506375272[37] = 0;
   out_2978169847506375272[38] = 0;
   out_2978169847506375272[39] = 0;
   out_2978169847506375272[40] = 1;
   out_2978169847506375272[41] = 0;
   out_2978169847506375272[42] = 0;
   out_2978169847506375272[43] = 0;
   out_2978169847506375272[44] = 0;
   out_2978169847506375272[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_2978169847506375272[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_2978169847506375272[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_2978169847506375272[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_2978169847506375272[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_2978169847506375272[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_2978169847506375272[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_2978169847506375272[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_2978169847506375272[53] = -9.8100000000000005*dt;
   out_2978169847506375272[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_2978169847506375272[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_2978169847506375272[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_2978169847506375272[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_2978169847506375272[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_2978169847506375272[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_2978169847506375272[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_2978169847506375272[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_2978169847506375272[62] = 0;
   out_2978169847506375272[63] = 0;
   out_2978169847506375272[64] = 0;
   out_2978169847506375272[65] = 0;
   out_2978169847506375272[66] = 0;
   out_2978169847506375272[67] = 0;
   out_2978169847506375272[68] = 0;
   out_2978169847506375272[69] = 0;
   out_2978169847506375272[70] = 1;
   out_2978169847506375272[71] = 0;
   out_2978169847506375272[72] = 0;
   out_2978169847506375272[73] = 0;
   out_2978169847506375272[74] = 0;
   out_2978169847506375272[75] = 0;
   out_2978169847506375272[76] = 0;
   out_2978169847506375272[77] = 0;
   out_2978169847506375272[78] = 0;
   out_2978169847506375272[79] = 0;
   out_2978169847506375272[80] = 1;
}
void h_25(double *state, double *unused, double *out_4652885364343750448) {
   out_4652885364343750448[0] = state[6];
}
void H_25(double *state, double *unused, double *out_1635374662770778876) {
   out_1635374662770778876[0] = 0;
   out_1635374662770778876[1] = 0;
   out_1635374662770778876[2] = 0;
   out_1635374662770778876[3] = 0;
   out_1635374662770778876[4] = 0;
   out_1635374662770778876[5] = 0;
   out_1635374662770778876[6] = 1;
   out_1635374662770778876[7] = 0;
   out_1635374662770778876[8] = 0;
}
void h_24(double *state, double *unused, double *out_1850369176656129099) {
   out_1850369176656129099[0] = state[4];
   out_1850369176656129099[1] = state[5];
}
void H_24(double *state, double *unused, double *out_537274936234720690) {
   out_537274936234720690[0] = 0;
   out_537274936234720690[1] = 0;
   out_537274936234720690[2] = 0;
   out_537274936234720690[3] = 0;
   out_537274936234720690[4] = 1;
   out_537274936234720690[5] = 0;
   out_537274936234720690[6] = 0;
   out_537274936234720690[7] = 0;
   out_537274936234720690[8] = 0;
   out_537274936234720690[9] = 0;
   out_537274936234720690[10] = 0;
   out_537274936234720690[11] = 0;
   out_537274936234720690[12] = 0;
   out_537274936234720690[13] = 0;
   out_537274936234720690[14] = 1;
   out_537274936234720690[15] = 0;
   out_537274936234720690[16] = 0;
   out_537274936234720690[17] = 0;
}
void h_30(double *state, double *unused, double *out_3986992112374791436) {
   out_3986992112374791436[0] = state[4];
}
void H_30(double *state, double *unused, double *out_4153707621278027503) {
   out_4153707621278027503[0] = 0;
   out_4153707621278027503[1] = 0;
   out_4153707621278027503[2] = 0;
   out_4153707621278027503[3] = 0;
   out_4153707621278027503[4] = 1;
   out_4153707621278027503[5] = 0;
   out_4153707621278027503[6] = 0;
   out_4153707621278027503[7] = 0;
   out_4153707621278027503[8] = 0;
}
void h_26(double *state, double *unused, double *out_3448151322053909377) {
   out_3448151322053909377[0] = state[7];
}
void H_26(double *state, double *unused, double *out_4939900632531579477) {
   out_4939900632531579477[0] = 0;
   out_4939900632531579477[1] = 0;
   out_4939900632531579477[2] = 0;
   out_4939900632531579477[3] = 0;
   out_4939900632531579477[4] = 0;
   out_4939900632531579477[5] = 0;
   out_4939900632531579477[6] = 0;
   out_4939900632531579477[7] = 1;
   out_4939900632531579477[8] = 0;
}
void h_27(double *state, double *unused, double *out_4773315296925324726) {
   out_4773315296925324726[0] = state[3];
}
void H_27(double *state, double *unused, double *out_6377301692461970720) {
   out_6377301692461970720[0] = 0;
   out_6377301692461970720[1] = 0;
   out_6377301692461970720[2] = 0;
   out_6377301692461970720[3] = 1;
   out_6377301692461970720[4] = 0;
   out_6377301692461970720[5] = 0;
   out_6377301692461970720[6] = 0;
   out_6377301692461970720[7] = 0;
   out_6377301692461970720[8] = 0;
}
void h_29(double *state, double *unused, double *out_4930501965276453871) {
   out_4930501965276453871[0] = state[1];
}
void H_29(double *state, double *unused, double *out_4663938965592419687) {
   out_4663938965592419687[0] = 0;
   out_4663938965592419687[1] = 1;
   out_4663938965592419687[2] = 0;
   out_4663938965592419687[3] = 0;
   out_4663938965592419687[4] = 0;
   out_4663938965592419687[5] = 0;
   out_4663938965592419687[6] = 0;
   out_4663938965592419687[7] = 0;
   out_4663938965592419687[8] = 0;
}
void h_28(double *state, double *unused, double *out_7810101348369657411) {
   out_7810101348369657411[0] = state[0];
}
void H_28(double *state, double *unused, double *out_418460051477110887) {
   out_418460051477110887[0] = 1;
   out_418460051477110887[1] = 0;
   out_418460051477110887[2] = 0;
   out_418460051477110887[3] = 0;
   out_418460051477110887[4] = 0;
   out_418460051477110887[5] = 0;
   out_418460051477110887[6] = 0;
   out_418460051477110887[7] = 0;
   out_418460051477110887[8] = 0;
}
void h_31(double *state, double *unused, double *out_9129956871281942907) {
   out_9129956871281942907[0] = state[8];
}
void H_31(double *state, double *unused, double *out_2732336758336628824) {
   out_2732336758336628824[0] = 0;
   out_2732336758336628824[1] = 0;
   out_2732336758336628824[2] = 0;
   out_2732336758336628824[3] = 0;
   out_2732336758336628824[4] = 0;
   out_2732336758336628824[5] = 0;
   out_2732336758336628824[6] = 0;
   out_2732336758336628824[7] = 0;
   out_2732336758336628824[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_3194710944048673507) {
  err_fun(nom_x, delta_x, out_3194710944048673507);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_8039664853018696099) {
  inv_err_fun(nom_x, true_x, out_8039664853018696099);
}
void car_H_mod_fun(double *state, double *out_5587385678613239193) {
  H_mod_fun(state, out_5587385678613239193);
}
void car_f_fun(double *state, double dt, double *out_7292828168458319052) {
  f_fun(state,  dt, out_7292828168458319052);
}
void car_F_fun(double *state, double dt, double *out_2978169847506375272) {
  F_fun(state,  dt, out_2978169847506375272);
}
void car_h_25(double *state, double *unused, double *out_4652885364343750448) {
  h_25(state, unused, out_4652885364343750448);
}
void car_H_25(double *state, double *unused, double *out_1635374662770778876) {
  H_25(state, unused, out_1635374662770778876);
}
void car_h_24(double *state, double *unused, double *out_1850369176656129099) {
  h_24(state, unused, out_1850369176656129099);
}
void car_H_24(double *state, double *unused, double *out_537274936234720690) {
  H_24(state, unused, out_537274936234720690);
}
void car_h_30(double *state, double *unused, double *out_3986992112374791436) {
  h_30(state, unused, out_3986992112374791436);
}
void car_H_30(double *state, double *unused, double *out_4153707621278027503) {
  H_30(state, unused, out_4153707621278027503);
}
void car_h_26(double *state, double *unused, double *out_3448151322053909377) {
  h_26(state, unused, out_3448151322053909377);
}
void car_H_26(double *state, double *unused, double *out_4939900632531579477) {
  H_26(state, unused, out_4939900632531579477);
}
void car_h_27(double *state, double *unused, double *out_4773315296925324726) {
  h_27(state, unused, out_4773315296925324726);
}
void car_H_27(double *state, double *unused, double *out_6377301692461970720) {
  H_27(state, unused, out_6377301692461970720);
}
void car_h_29(double *state, double *unused, double *out_4930501965276453871) {
  h_29(state, unused, out_4930501965276453871);
}
void car_H_29(double *state, double *unused, double *out_4663938965592419687) {
  H_29(state, unused, out_4663938965592419687);
}
void car_h_28(double *state, double *unused, double *out_7810101348369657411) {
  h_28(state, unused, out_7810101348369657411);
}
void car_H_28(double *state, double *unused, double *out_418460051477110887) {
  H_28(state, unused, out_418460051477110887);
}
void car_h_31(double *state, double *unused, double *out_9129956871281942907) {
  h_31(state, unused, out_9129956871281942907);
}
void car_H_31(double *state, double *unused, double *out_2732336758336628824) {
  H_31(state, unused, out_2732336758336628824);
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
