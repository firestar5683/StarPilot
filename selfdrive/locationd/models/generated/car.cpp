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
 *                       Code generated with SymPy 1.12                       *
 *                                                                            *
 *              See http://www.sympy.org/ for more information.               *
 *                                                                            *
 *                         This file is part of 'ekf'                         *
 ******************************************************************************/
void err_fun(double *nom_x, double *delta_x, double *out_1185780684525753826) {
   out_1185780684525753826[0] = delta_x[0] + nom_x[0];
   out_1185780684525753826[1] = delta_x[1] + nom_x[1];
   out_1185780684525753826[2] = delta_x[2] + nom_x[2];
   out_1185780684525753826[3] = delta_x[3] + nom_x[3];
   out_1185780684525753826[4] = delta_x[4] + nom_x[4];
   out_1185780684525753826[5] = delta_x[5] + nom_x[5];
   out_1185780684525753826[6] = delta_x[6] + nom_x[6];
   out_1185780684525753826[7] = delta_x[7] + nom_x[7];
   out_1185780684525753826[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_1174316818242049591) {
   out_1174316818242049591[0] = -nom_x[0] + true_x[0];
   out_1174316818242049591[1] = -nom_x[1] + true_x[1];
   out_1174316818242049591[2] = -nom_x[2] + true_x[2];
   out_1174316818242049591[3] = -nom_x[3] + true_x[3];
   out_1174316818242049591[4] = -nom_x[4] + true_x[4];
   out_1174316818242049591[5] = -nom_x[5] + true_x[5];
   out_1174316818242049591[6] = -nom_x[6] + true_x[6];
   out_1174316818242049591[7] = -nom_x[7] + true_x[7];
   out_1174316818242049591[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_2505241908779746070) {
   out_2505241908779746070[0] = 1.0;
   out_2505241908779746070[1] = 0;
   out_2505241908779746070[2] = 0;
   out_2505241908779746070[3] = 0;
   out_2505241908779746070[4] = 0;
   out_2505241908779746070[5] = 0;
   out_2505241908779746070[6] = 0;
   out_2505241908779746070[7] = 0;
   out_2505241908779746070[8] = 0;
   out_2505241908779746070[9] = 0;
   out_2505241908779746070[10] = 1.0;
   out_2505241908779746070[11] = 0;
   out_2505241908779746070[12] = 0;
   out_2505241908779746070[13] = 0;
   out_2505241908779746070[14] = 0;
   out_2505241908779746070[15] = 0;
   out_2505241908779746070[16] = 0;
   out_2505241908779746070[17] = 0;
   out_2505241908779746070[18] = 0;
   out_2505241908779746070[19] = 0;
   out_2505241908779746070[20] = 1.0;
   out_2505241908779746070[21] = 0;
   out_2505241908779746070[22] = 0;
   out_2505241908779746070[23] = 0;
   out_2505241908779746070[24] = 0;
   out_2505241908779746070[25] = 0;
   out_2505241908779746070[26] = 0;
   out_2505241908779746070[27] = 0;
   out_2505241908779746070[28] = 0;
   out_2505241908779746070[29] = 0;
   out_2505241908779746070[30] = 1.0;
   out_2505241908779746070[31] = 0;
   out_2505241908779746070[32] = 0;
   out_2505241908779746070[33] = 0;
   out_2505241908779746070[34] = 0;
   out_2505241908779746070[35] = 0;
   out_2505241908779746070[36] = 0;
   out_2505241908779746070[37] = 0;
   out_2505241908779746070[38] = 0;
   out_2505241908779746070[39] = 0;
   out_2505241908779746070[40] = 1.0;
   out_2505241908779746070[41] = 0;
   out_2505241908779746070[42] = 0;
   out_2505241908779746070[43] = 0;
   out_2505241908779746070[44] = 0;
   out_2505241908779746070[45] = 0;
   out_2505241908779746070[46] = 0;
   out_2505241908779746070[47] = 0;
   out_2505241908779746070[48] = 0;
   out_2505241908779746070[49] = 0;
   out_2505241908779746070[50] = 1.0;
   out_2505241908779746070[51] = 0;
   out_2505241908779746070[52] = 0;
   out_2505241908779746070[53] = 0;
   out_2505241908779746070[54] = 0;
   out_2505241908779746070[55] = 0;
   out_2505241908779746070[56] = 0;
   out_2505241908779746070[57] = 0;
   out_2505241908779746070[58] = 0;
   out_2505241908779746070[59] = 0;
   out_2505241908779746070[60] = 1.0;
   out_2505241908779746070[61] = 0;
   out_2505241908779746070[62] = 0;
   out_2505241908779746070[63] = 0;
   out_2505241908779746070[64] = 0;
   out_2505241908779746070[65] = 0;
   out_2505241908779746070[66] = 0;
   out_2505241908779746070[67] = 0;
   out_2505241908779746070[68] = 0;
   out_2505241908779746070[69] = 0;
   out_2505241908779746070[70] = 1.0;
   out_2505241908779746070[71] = 0;
   out_2505241908779746070[72] = 0;
   out_2505241908779746070[73] = 0;
   out_2505241908779746070[74] = 0;
   out_2505241908779746070[75] = 0;
   out_2505241908779746070[76] = 0;
   out_2505241908779746070[77] = 0;
   out_2505241908779746070[78] = 0;
   out_2505241908779746070[79] = 0;
   out_2505241908779746070[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_452792739136803459) {
   out_452792739136803459[0] = state[0];
   out_452792739136803459[1] = state[1];
   out_452792739136803459[2] = state[2];
   out_452792739136803459[3] = state[3];
   out_452792739136803459[4] = state[4];
   out_452792739136803459[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8000000000000007*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_452792739136803459[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_452792739136803459[7] = state[7];
   out_452792739136803459[8] = state[8];
}
void F_fun(double *state, double dt, double *out_1931282010731613084) {
   out_1931282010731613084[0] = 1;
   out_1931282010731613084[1] = 0;
   out_1931282010731613084[2] = 0;
   out_1931282010731613084[3] = 0;
   out_1931282010731613084[4] = 0;
   out_1931282010731613084[5] = 0;
   out_1931282010731613084[6] = 0;
   out_1931282010731613084[7] = 0;
   out_1931282010731613084[8] = 0;
   out_1931282010731613084[9] = 0;
   out_1931282010731613084[10] = 1;
   out_1931282010731613084[11] = 0;
   out_1931282010731613084[12] = 0;
   out_1931282010731613084[13] = 0;
   out_1931282010731613084[14] = 0;
   out_1931282010731613084[15] = 0;
   out_1931282010731613084[16] = 0;
   out_1931282010731613084[17] = 0;
   out_1931282010731613084[18] = 0;
   out_1931282010731613084[19] = 0;
   out_1931282010731613084[20] = 1;
   out_1931282010731613084[21] = 0;
   out_1931282010731613084[22] = 0;
   out_1931282010731613084[23] = 0;
   out_1931282010731613084[24] = 0;
   out_1931282010731613084[25] = 0;
   out_1931282010731613084[26] = 0;
   out_1931282010731613084[27] = 0;
   out_1931282010731613084[28] = 0;
   out_1931282010731613084[29] = 0;
   out_1931282010731613084[30] = 1;
   out_1931282010731613084[31] = 0;
   out_1931282010731613084[32] = 0;
   out_1931282010731613084[33] = 0;
   out_1931282010731613084[34] = 0;
   out_1931282010731613084[35] = 0;
   out_1931282010731613084[36] = 0;
   out_1931282010731613084[37] = 0;
   out_1931282010731613084[38] = 0;
   out_1931282010731613084[39] = 0;
   out_1931282010731613084[40] = 1;
   out_1931282010731613084[41] = 0;
   out_1931282010731613084[42] = 0;
   out_1931282010731613084[43] = 0;
   out_1931282010731613084[44] = 0;
   out_1931282010731613084[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_1931282010731613084[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_1931282010731613084[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_1931282010731613084[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_1931282010731613084[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_1931282010731613084[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_1931282010731613084[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_1931282010731613084[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_1931282010731613084[53] = -9.8000000000000007*dt;
   out_1931282010731613084[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_1931282010731613084[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_1931282010731613084[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_1931282010731613084[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_1931282010731613084[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_1931282010731613084[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_1931282010731613084[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_1931282010731613084[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_1931282010731613084[62] = 0;
   out_1931282010731613084[63] = 0;
   out_1931282010731613084[64] = 0;
   out_1931282010731613084[65] = 0;
   out_1931282010731613084[66] = 0;
   out_1931282010731613084[67] = 0;
   out_1931282010731613084[68] = 0;
   out_1931282010731613084[69] = 0;
   out_1931282010731613084[70] = 1;
   out_1931282010731613084[71] = 0;
   out_1931282010731613084[72] = 0;
   out_1931282010731613084[73] = 0;
   out_1931282010731613084[74] = 0;
   out_1931282010731613084[75] = 0;
   out_1931282010731613084[76] = 0;
   out_1931282010731613084[77] = 0;
   out_1931282010731613084[78] = 0;
   out_1931282010731613084[79] = 0;
   out_1931282010731613084[80] = 1;
}
void h_25(double *state, double *unused, double *out_1974802446302882690) {
   out_1974802446302882690[0] = state[6];
}
void H_25(double *state, double *unused, double *out_6388820959049565918) {
   out_6388820959049565918[0] = 0;
   out_6388820959049565918[1] = 0;
   out_6388820959049565918[2] = 0;
   out_6388820959049565918[3] = 0;
   out_6388820959049565918[4] = 0;
   out_6388820959049565918[5] = 0;
   out_6388820959049565918[6] = 1;
   out_6388820959049565918[7] = 0;
   out_6388820959049565918[8] = 0;
}
void h_24(double *state, double *unused, double *out_2969763034076471220) {
   out_2969763034076471220[0] = state[4];
   out_2969763034076471220[1] = state[5];
}
void H_24(double *state, double *unused, double *out_5918363477006227194) {
   out_5918363477006227194[0] = 0;
   out_5918363477006227194[1] = 0;
   out_5918363477006227194[2] = 0;
   out_5918363477006227194[3] = 0;
   out_5918363477006227194[4] = 1;
   out_5918363477006227194[5] = 0;
   out_5918363477006227194[6] = 0;
   out_5918363477006227194[7] = 0;
   out_5918363477006227194[8] = 0;
   out_5918363477006227194[9] = 0;
   out_5918363477006227194[10] = 0;
   out_5918363477006227194[11] = 0;
   out_5918363477006227194[12] = 0;
   out_5918363477006227194[13] = 0;
   out_5918363477006227194[14] = 1;
   out_5918363477006227194[15] = 0;
   out_5918363477006227194[16] = 0;
   out_5918363477006227194[17] = 0;
}
void h_30(double *state, double *unused, double *out_6469354174236507603) {
   out_6469354174236507603[0] = state[4];
}
void H_30(double *state, double *unused, double *out_6259482011906325848) {
   out_6259482011906325848[0] = 0;
   out_6259482011906325848[1] = 0;
   out_6259482011906325848[2] = 0;
   out_6259482011906325848[3] = 0;
   out_6259482011906325848[4] = 1;
   out_6259482011906325848[5] = 0;
   out_6259482011906325848[6] = 0;
   out_6259482011906325848[7] = 0;
   out_6259482011906325848[8] = 0;
}
void h_26(double *state, double *unused, double *out_1467680906575661958) {
   out_1467680906575661958[0] = state[7];
}
void H_26(double *state, double *unused, double *out_2647317640175509694) {
   out_2647317640175509694[0] = 0;
   out_2647317640175509694[1] = 0;
   out_2647317640175509694[2] = 0;
   out_2647317640175509694[3] = 0;
   out_2647317640175509694[4] = 0;
   out_2647317640175509694[5] = 0;
   out_2647317640175509694[6] = 0;
   out_2647317640175509694[7] = 1;
   out_2647317640175509694[8] = 0;
}
void h_27(double *state, double *unused, double *out_5460340988125818123) {
   out_5460340988125818123[0] = state[3];
}
void H_27(double *state, double *unused, double *out_4084718700105900937) {
   out_4084718700105900937[0] = 0;
   out_4084718700105900937[1] = 0;
   out_4084718700105900937[2] = 0;
   out_4084718700105900937[3] = 1;
   out_4084718700105900937[4] = 0;
   out_4084718700105900937[5] = 0;
   out_4084718700105900937[6] = 0;
   out_4084718700105900937[7] = 0;
   out_4084718700105900937[8] = 0;
}
void h_29(double *state, double *unused, double *out_5185146925841312234) {
   out_5185146925841312234[0] = state[1];
}
void H_29(double *state, double *unused, double *out_2371355973236349904) {
   out_2371355973236349904[0] = 0;
   out_2371355973236349904[1] = 1;
   out_2371355973236349904[2] = 0;
   out_2371355973236349904[3] = 0;
   out_2371355973236349904[4] = 0;
   out_2371355973236349904[5] = 0;
   out_2371355973236349904[6] = 0;
   out_2371355973236349904[7] = 0;
   out_2371355973236349904[8] = 0;
}
void h_28(double *state, double *unused, double *out_458667720464972478) {
   out_458667720464972478[0] = state[0];
}
void H_28(double *state, double *unused, double *out_2711043043833180670) {
   out_2711043043833180670[0] = 1;
   out_2711043043833180670[1] = 0;
   out_2711043043833180670[2] = 0;
   out_2711043043833180670[3] = 0;
   out_2711043043833180670[4] = 0;
   out_2711043043833180670[5] = 0;
   out_2711043043833180670[6] = 0;
   out_2711043043833180670[7] = 0;
   out_2711043043833180670[8] = 0;
}
void h_31(double *state, double *unused, double *out_8745637672653233626) {
   out_8745637672653233626[0] = state[8];
}
void H_31(double *state, double *unused, double *out_6419466920926526346) {
   out_6419466920926526346[0] = 0;
   out_6419466920926526346[1] = 0;
   out_6419466920926526346[2] = 0;
   out_6419466920926526346[3] = 0;
   out_6419466920926526346[4] = 0;
   out_6419466920926526346[5] = 0;
   out_6419466920926526346[6] = 0;
   out_6419466920926526346[7] = 0;
   out_6419466920926526346[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_1185780684525753826) {
  err_fun(nom_x, delta_x, out_1185780684525753826);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_1174316818242049591) {
  inv_err_fun(nom_x, true_x, out_1174316818242049591);
}
void car_H_mod_fun(double *state, double *out_2505241908779746070) {
  H_mod_fun(state, out_2505241908779746070);
}
void car_f_fun(double *state, double dt, double *out_452792739136803459) {
  f_fun(state,  dt, out_452792739136803459);
}
void car_F_fun(double *state, double dt, double *out_1931282010731613084) {
  F_fun(state,  dt, out_1931282010731613084);
}
void car_h_25(double *state, double *unused, double *out_1974802446302882690) {
  h_25(state, unused, out_1974802446302882690);
}
void car_H_25(double *state, double *unused, double *out_6388820959049565918) {
  H_25(state, unused, out_6388820959049565918);
}
void car_h_24(double *state, double *unused, double *out_2969763034076471220) {
  h_24(state, unused, out_2969763034076471220);
}
void car_H_24(double *state, double *unused, double *out_5918363477006227194) {
  H_24(state, unused, out_5918363477006227194);
}
void car_h_30(double *state, double *unused, double *out_6469354174236507603) {
  h_30(state, unused, out_6469354174236507603);
}
void car_H_30(double *state, double *unused, double *out_6259482011906325848) {
  H_30(state, unused, out_6259482011906325848);
}
void car_h_26(double *state, double *unused, double *out_1467680906575661958) {
  h_26(state, unused, out_1467680906575661958);
}
void car_H_26(double *state, double *unused, double *out_2647317640175509694) {
  H_26(state, unused, out_2647317640175509694);
}
void car_h_27(double *state, double *unused, double *out_5460340988125818123) {
  h_27(state, unused, out_5460340988125818123);
}
void car_H_27(double *state, double *unused, double *out_4084718700105900937) {
  H_27(state, unused, out_4084718700105900937);
}
void car_h_29(double *state, double *unused, double *out_5185146925841312234) {
  h_29(state, unused, out_5185146925841312234);
}
void car_H_29(double *state, double *unused, double *out_2371355973236349904) {
  H_29(state, unused, out_2371355973236349904);
}
void car_h_28(double *state, double *unused, double *out_458667720464972478) {
  h_28(state, unused, out_458667720464972478);
}
void car_H_28(double *state, double *unused, double *out_2711043043833180670) {
  H_28(state, unused, out_2711043043833180670);
}
void car_h_31(double *state, double *unused, double *out_8745637672653233626) {
  h_31(state, unused, out_8745637672653233626);
}
void car_H_31(double *state, double *unused, double *out_6419466920926526346) {
  H_31(state, unused, out_6419466920926526346);
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
