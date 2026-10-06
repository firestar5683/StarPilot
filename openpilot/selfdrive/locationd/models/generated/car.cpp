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
void err_fun(double *nom_x, double *delta_x, double *out_9094620970440409675) {
   out_9094620970440409675[0] = delta_x[0] + nom_x[0];
   out_9094620970440409675[1] = delta_x[1] + nom_x[1];
   out_9094620970440409675[2] = delta_x[2] + nom_x[2];
   out_9094620970440409675[3] = delta_x[3] + nom_x[3];
   out_9094620970440409675[4] = delta_x[4] + nom_x[4];
   out_9094620970440409675[5] = delta_x[5] + nom_x[5];
   out_9094620970440409675[6] = delta_x[6] + nom_x[6];
   out_9094620970440409675[7] = delta_x[7] + nom_x[7];
   out_9094620970440409675[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_4808598882803507141) {
   out_4808598882803507141[0] = -nom_x[0] + true_x[0];
   out_4808598882803507141[1] = -nom_x[1] + true_x[1];
   out_4808598882803507141[2] = -nom_x[2] + true_x[2];
   out_4808598882803507141[3] = -nom_x[3] + true_x[3];
   out_4808598882803507141[4] = -nom_x[4] + true_x[4];
   out_4808598882803507141[5] = -nom_x[5] + true_x[5];
   out_4808598882803507141[6] = -nom_x[6] + true_x[6];
   out_4808598882803507141[7] = -nom_x[7] + true_x[7];
   out_4808598882803507141[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_3453018442672977703) {
   out_3453018442672977703[0] = 1.0;
   out_3453018442672977703[1] = 0.0;
   out_3453018442672977703[2] = 0.0;
   out_3453018442672977703[3] = 0.0;
   out_3453018442672977703[4] = 0.0;
   out_3453018442672977703[5] = 0.0;
   out_3453018442672977703[6] = 0.0;
   out_3453018442672977703[7] = 0.0;
   out_3453018442672977703[8] = 0.0;
   out_3453018442672977703[9] = 0.0;
   out_3453018442672977703[10] = 1.0;
   out_3453018442672977703[11] = 0.0;
   out_3453018442672977703[12] = 0.0;
   out_3453018442672977703[13] = 0.0;
   out_3453018442672977703[14] = 0.0;
   out_3453018442672977703[15] = 0.0;
   out_3453018442672977703[16] = 0.0;
   out_3453018442672977703[17] = 0.0;
   out_3453018442672977703[18] = 0.0;
   out_3453018442672977703[19] = 0.0;
   out_3453018442672977703[20] = 1.0;
   out_3453018442672977703[21] = 0.0;
   out_3453018442672977703[22] = 0.0;
   out_3453018442672977703[23] = 0.0;
   out_3453018442672977703[24] = 0.0;
   out_3453018442672977703[25] = 0.0;
   out_3453018442672977703[26] = 0.0;
   out_3453018442672977703[27] = 0.0;
   out_3453018442672977703[28] = 0.0;
   out_3453018442672977703[29] = 0.0;
   out_3453018442672977703[30] = 1.0;
   out_3453018442672977703[31] = 0.0;
   out_3453018442672977703[32] = 0.0;
   out_3453018442672977703[33] = 0.0;
   out_3453018442672977703[34] = 0.0;
   out_3453018442672977703[35] = 0.0;
   out_3453018442672977703[36] = 0.0;
   out_3453018442672977703[37] = 0.0;
   out_3453018442672977703[38] = 0.0;
   out_3453018442672977703[39] = 0.0;
   out_3453018442672977703[40] = 1.0;
   out_3453018442672977703[41] = 0.0;
   out_3453018442672977703[42] = 0.0;
   out_3453018442672977703[43] = 0.0;
   out_3453018442672977703[44] = 0.0;
   out_3453018442672977703[45] = 0.0;
   out_3453018442672977703[46] = 0.0;
   out_3453018442672977703[47] = 0.0;
   out_3453018442672977703[48] = 0.0;
   out_3453018442672977703[49] = 0.0;
   out_3453018442672977703[50] = 1.0;
   out_3453018442672977703[51] = 0.0;
   out_3453018442672977703[52] = 0.0;
   out_3453018442672977703[53] = 0.0;
   out_3453018442672977703[54] = 0.0;
   out_3453018442672977703[55] = 0.0;
   out_3453018442672977703[56] = 0.0;
   out_3453018442672977703[57] = 0.0;
   out_3453018442672977703[58] = 0.0;
   out_3453018442672977703[59] = 0.0;
   out_3453018442672977703[60] = 1.0;
   out_3453018442672977703[61] = 0.0;
   out_3453018442672977703[62] = 0.0;
   out_3453018442672977703[63] = 0.0;
   out_3453018442672977703[64] = 0.0;
   out_3453018442672977703[65] = 0.0;
   out_3453018442672977703[66] = 0.0;
   out_3453018442672977703[67] = 0.0;
   out_3453018442672977703[68] = 0.0;
   out_3453018442672977703[69] = 0.0;
   out_3453018442672977703[70] = 1.0;
   out_3453018442672977703[71] = 0.0;
   out_3453018442672977703[72] = 0.0;
   out_3453018442672977703[73] = 0.0;
   out_3453018442672977703[74] = 0.0;
   out_3453018442672977703[75] = 0.0;
   out_3453018442672977703[76] = 0.0;
   out_3453018442672977703[77] = 0.0;
   out_3453018442672977703[78] = 0.0;
   out_3453018442672977703[79] = 0.0;
   out_3453018442672977703[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_2361277581367117895) {
   out_2361277581367117895[0] = state[0];
   out_2361277581367117895[1] = state[1];
   out_2361277581367117895[2] = state[2];
   out_2361277581367117895[3] = state[3];
   out_2361277581367117895[4] = state[4];
   out_2361277581367117895[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_2361277581367117895[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_2361277581367117895[7] = state[7];
   out_2361277581367117895[8] = state[8];
}
void F_fun(double *state, double dt, double *out_5103437232056083059) {
   out_5103437232056083059[0] = 1;
   out_5103437232056083059[1] = 0;
   out_5103437232056083059[2] = 0;
   out_5103437232056083059[3] = 0;
   out_5103437232056083059[4] = 0;
   out_5103437232056083059[5] = 0;
   out_5103437232056083059[6] = 0;
   out_5103437232056083059[7] = 0;
   out_5103437232056083059[8] = 0;
   out_5103437232056083059[9] = 0;
   out_5103437232056083059[10] = 1;
   out_5103437232056083059[11] = 0;
   out_5103437232056083059[12] = 0;
   out_5103437232056083059[13] = 0;
   out_5103437232056083059[14] = 0;
   out_5103437232056083059[15] = 0;
   out_5103437232056083059[16] = 0;
   out_5103437232056083059[17] = 0;
   out_5103437232056083059[18] = 0;
   out_5103437232056083059[19] = 0;
   out_5103437232056083059[20] = 1;
   out_5103437232056083059[21] = 0;
   out_5103437232056083059[22] = 0;
   out_5103437232056083059[23] = 0;
   out_5103437232056083059[24] = 0;
   out_5103437232056083059[25] = 0;
   out_5103437232056083059[26] = 0;
   out_5103437232056083059[27] = 0;
   out_5103437232056083059[28] = 0;
   out_5103437232056083059[29] = 0;
   out_5103437232056083059[30] = 1;
   out_5103437232056083059[31] = 0;
   out_5103437232056083059[32] = 0;
   out_5103437232056083059[33] = 0;
   out_5103437232056083059[34] = 0;
   out_5103437232056083059[35] = 0;
   out_5103437232056083059[36] = 0;
   out_5103437232056083059[37] = 0;
   out_5103437232056083059[38] = 0;
   out_5103437232056083059[39] = 0;
   out_5103437232056083059[40] = 1;
   out_5103437232056083059[41] = 0;
   out_5103437232056083059[42] = 0;
   out_5103437232056083059[43] = 0;
   out_5103437232056083059[44] = 0;
   out_5103437232056083059[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_5103437232056083059[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_5103437232056083059[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_5103437232056083059[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_5103437232056083059[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_5103437232056083059[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_5103437232056083059[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_5103437232056083059[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_5103437232056083059[53] = -9.8100000000000005*dt;
   out_5103437232056083059[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_5103437232056083059[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_5103437232056083059[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_5103437232056083059[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_5103437232056083059[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_5103437232056083059[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_5103437232056083059[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_5103437232056083059[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_5103437232056083059[62] = 0;
   out_5103437232056083059[63] = 0;
   out_5103437232056083059[64] = 0;
   out_5103437232056083059[65] = 0;
   out_5103437232056083059[66] = 0;
   out_5103437232056083059[67] = 0;
   out_5103437232056083059[68] = 0;
   out_5103437232056083059[69] = 0;
   out_5103437232056083059[70] = 1;
   out_5103437232056083059[71] = 0;
   out_5103437232056083059[72] = 0;
   out_5103437232056083059[73] = 0;
   out_5103437232056083059[74] = 0;
   out_5103437232056083059[75] = 0;
   out_5103437232056083059[76] = 0;
   out_5103437232056083059[77] = 0;
   out_5103437232056083059[78] = 0;
   out_5103437232056083059[79] = 0;
   out_5103437232056083059[80] = 1;
}
void h_25(double *state, double *unused, double *out_948931866886974125) {
   out_948931866886974125[0] = state[6];
}
void H_25(double *state, double *unused, double *out_69962207316513974) {
   out_69962207316513974[0] = 0;
   out_69962207316513974[1] = 0;
   out_69962207316513974[2] = 0;
   out_69962207316513974[3] = 0;
   out_69962207316513974[4] = 0;
   out_69962207316513974[5] = 0;
   out_69962207316513974[6] = 1;
   out_69962207316513974[7] = 0;
   out_69962207316513974[8] = 0;
}
void h_24(double *state, double *unused, double *out_6581862240582867615) {
   out_6581862240582867615[0] = state[4];
   out_6581862240582867615[1] = state[5];
}
void H_24(double *state, double *unused, double *out_3627887806118837110) {
   out_3627887806118837110[0] = 0;
   out_3627887806118837110[1] = 0;
   out_3627887806118837110[2] = 0;
   out_3627887806118837110[3] = 0;
   out_3627887806118837110[4] = 1;
   out_3627887806118837110[5] = 0;
   out_3627887806118837110[6] = 0;
   out_3627887806118837110[7] = 0;
   out_3627887806118837110[8] = 0;
   out_3627887806118837110[9] = 0;
   out_3627887806118837110[10] = 0;
   out_3627887806118837110[11] = 0;
   out_3627887806118837110[12] = 0;
   out_3627887806118837110[13] = 0;
   out_3627887806118837110[14] = 1;
   out_3627887806118837110[15] = 0;
   out_3627887806118837110[16] = 0;
   out_3627887806118837110[17] = 0;
}
void h_30(double *state, double *unused, double *out_4586381395140996475) {
   out_4586381395140996475[0] = state[4];
}
void H_30(double *state, double *unused, double *out_59376739826726096) {
   out_59376739826726096[0] = 0;
   out_59376739826726096[1] = 0;
   out_59376739826726096[2] = 0;
   out_59376739826726096[3] = 0;
   out_59376739826726096[4] = 1;
   out_59376739826726096[5] = 0;
   out_59376739826726096[6] = 0;
   out_59376739826726096[7] = 0;
   out_59376739826726096[8] = 0;
}
void h_26(double *state, double *unused, double *out_5529891248042658910) {
   out_5529891248042658910[0] = state[7];
}
void H_26(double *state, double *unused, double *out_3671541111557542250) {
   out_3671541111557542250[0] = 0;
   out_3671541111557542250[1] = 0;
   out_3671541111557542250[2] = 0;
   out_3671541111557542250[3] = 0;
   out_3671541111557542250[4] = 0;
   out_3671541111557542250[5] = 0;
   out_3671541111557542250[6] = 0;
   out_3671541111557542250[7] = 1;
   out_3671541111557542250[8] = 0;
}
void h_27(double *state, double *unused, double *out_1706782012047792935) {
   out_1706782012047792935[0] = state[3];
}
void H_27(double *state, double *unused, double *out_2234140051627151007) {
   out_2234140051627151007[0] = 0;
   out_2234140051627151007[1] = 0;
   out_2234140051627151007[2] = 0;
   out_2234140051627151007[3] = 1;
   out_2234140051627151007[4] = 0;
   out_2234140051627151007[5] = 0;
   out_2234140051627151007[6] = 0;
   out_2234140051627151007[7] = 0;
   out_2234140051627151007[8] = 0;
}
void h_29(double *state, double *unused, double *out_8858689410907709496) {
   out_8858689410907709496[0] = state[1];
}
void H_29(double *state, double *unused, double *out_450854604487666088) {
   out_450854604487666088[0] = 0;
   out_450854604487666088[1] = 1;
   out_450854604487666088[2] = 0;
   out_450854604487666088[3] = 0;
   out_450854604487666088[4] = 0;
   out_450854604487666088[5] = 0;
   out_450854604487666088[6] = 0;
   out_450854604487666088[7] = 0;
   out_450854604487666088[8] = 0;
}
void h_28(double *state, double *unused, double *out_2310097896724270452) {
   out_2310097896724270452[0] = state[0];
}
void H_28(double *state, double *unused, double *out_4631544412581864486) {
   out_4631544412581864486[0] = 1;
   out_4631544412581864486[1] = 0;
   out_4631544412581864486[2] = 0;
   out_4631544412581864486[3] = 0;
   out_4631544412581864486[4] = 0;
   out_4631544412581864486[5] = 0;
   out_4631544412581864486[6] = 0;
   out_4631544412581864486[7] = 0;
   out_4631544412581864486[8] = 0;
}
void h_31(double *state, double *unused, double *out_803412042666319154) {
   out_803412042666319154[0] = state[8];
}
void H_31(double *state, double *unused, double *out_100608169193474402) {
   out_100608169193474402[0] = 0;
   out_100608169193474402[1] = 0;
   out_100608169193474402[2] = 0;
   out_100608169193474402[3] = 0;
   out_100608169193474402[4] = 0;
   out_100608169193474402[5] = 0;
   out_100608169193474402[6] = 0;
   out_100608169193474402[7] = 0;
   out_100608169193474402[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_9094620970440409675) {
  err_fun(nom_x, delta_x, out_9094620970440409675);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_4808598882803507141) {
  inv_err_fun(nom_x, true_x, out_4808598882803507141);
}
void car_H_mod_fun(double *state, double *out_3453018442672977703) {
  H_mod_fun(state, out_3453018442672977703);
}
void car_f_fun(double *state, double dt, double *out_2361277581367117895) {
  f_fun(state,  dt, out_2361277581367117895);
}
void car_F_fun(double *state, double dt, double *out_5103437232056083059) {
  F_fun(state,  dt, out_5103437232056083059);
}
void car_h_25(double *state, double *unused, double *out_948931866886974125) {
  h_25(state, unused, out_948931866886974125);
}
void car_H_25(double *state, double *unused, double *out_69962207316513974) {
  H_25(state, unused, out_69962207316513974);
}
void car_h_24(double *state, double *unused, double *out_6581862240582867615) {
  h_24(state, unused, out_6581862240582867615);
}
void car_H_24(double *state, double *unused, double *out_3627887806118837110) {
  H_24(state, unused, out_3627887806118837110);
}
void car_h_30(double *state, double *unused, double *out_4586381395140996475) {
  h_30(state, unused, out_4586381395140996475);
}
void car_H_30(double *state, double *unused, double *out_59376739826726096) {
  H_30(state, unused, out_59376739826726096);
}
void car_h_26(double *state, double *unused, double *out_5529891248042658910) {
  h_26(state, unused, out_5529891248042658910);
}
void car_H_26(double *state, double *unused, double *out_3671541111557542250) {
  H_26(state, unused, out_3671541111557542250);
}
void car_h_27(double *state, double *unused, double *out_1706782012047792935) {
  h_27(state, unused, out_1706782012047792935);
}
void car_H_27(double *state, double *unused, double *out_2234140051627151007) {
  H_27(state, unused, out_2234140051627151007);
}
void car_h_29(double *state, double *unused, double *out_8858689410907709496) {
  h_29(state, unused, out_8858689410907709496);
}
void car_H_29(double *state, double *unused, double *out_450854604487666088) {
  H_29(state, unused, out_450854604487666088);
}
void car_h_28(double *state, double *unused, double *out_2310097896724270452) {
  h_28(state, unused, out_2310097896724270452);
}
void car_H_28(double *state, double *unused, double *out_4631544412581864486) {
  H_28(state, unused, out_4631544412581864486);
}
void car_h_31(double *state, double *unused, double *out_803412042666319154) {
  h_31(state, unused, out_803412042666319154);
}
void car_H_31(double *state, double *unused, double *out_100608169193474402) {
  H_31(state, unused, out_100608169193474402);
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
